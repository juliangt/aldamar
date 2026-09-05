"""Constantes del juego: colores ANSI, claves de menú y balance del turno."""

TITULO, VERDE, ROJO, AMARILLO, DIM = "1;36", "32", "31", "33", "2"

ESCRIBIR = "\x00texto"  # clave del menú que abre el modo tipeado clásico
OTRAS = "\x00otras"  # clave del menú que abre el submenú de gestiones

# Claves de los verbos con submenú: un verbo, un listado (issue 26). En el
# menú de acciones cada verbo es una sola entrada; elegirlo apila su
# listado y Esc vuelve al menú de abajo.
IR = "\x00ir"
TOMAR = "\x00tomar"
HABLAR = "\x00hablar"
RECLUTAR = "\x00reclutar"
COMPRAR = "\x00comprar"
USAR = "\x00usar"

# La tómbola del turno enemigo: el golpe normal tira con este peso, las
# habilidades con el suyo (declarado en el JSON).
PESO_GOLPE = 2
