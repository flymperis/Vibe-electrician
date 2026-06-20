from django.core.management.base import BaseCommand

from projects.models import Customer, Project, Quote


def _normalize_vat(value: str) -> str:
    return (value or "").strip()


def _find_or_create_customer(*, name: str, vat: str, phone: str, email: str, address: str) -> tuple[Customer, bool]:
    vat = _normalize_vat(vat)
    if vat:
        customer = Customer.objects.filter(vat__iexact=vat).first()
        if customer:
            return customer, False

    clean_name = (name or "").strip()
    if clean_name:
        customer = Customer.objects.filter(name__iexact=clean_name).first()
        if customer:
            return customer, False

    customer = Customer.objects.create(
        name=clean_name or "—",
        vat=vat,
        phone=(phone or "").strip(),
        email=(email or "").strip(),
        address=(address or "").strip(),
    )
    return customer, True


class Command(BaseCommand):
    help = "Δημιουργεί πελάτες από υπάρχουσες προσφορές και έργα και συνδέει FK"

    def handle(self, *args, **options):
        created = 0
        linked_quotes = 0
        linked_projects = 0

        for quote in Quote.objects.filter(customer__isnull=True).iterator():
            customer, was_created = _find_or_create_customer(
                name=quote.client_name,
                vat=quote.client_vat,
                phone=quote.client_phone,
                email=quote.client_email,
                address=quote.address,
            )
            if was_created:
                created += 1
            Quote.objects.filter(pk=quote.pk).update(customer=customer)
            linked_quotes += 1

        for project in Project.objects.filter(customer__isnull=True).iterator():
            quote = Quote.objects.filter(project_id=project.pk).first()
            if quote and quote.customer_id:
                Project.objects.filter(pk=project.pk).update(customer_id=quote.customer_id)
                linked_projects += 1
                continue
            customer, was_created = _find_or_create_customer(
                name=project.client_name,
                vat="",
                phone="",
                email="",
                address=project.address,
            )
            if was_created:
                created += 1
            Project.objects.filter(pk=project.pk).update(customer=customer)
            linked_projects += 1

        self.stdout.write(
            f"Done: {created} new customers, {linked_quotes} quotes, {linked_projects} projects linked."
        )
        self.stdout.write(f"Total customers: {Customer.objects.count()}")
