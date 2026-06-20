from django import template

register = template.Library()


@register.simple_tag
def quote_pdf_cell_style(column) -> str:
    return column.cell_style()
