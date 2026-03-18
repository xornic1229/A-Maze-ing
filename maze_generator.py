def create_empty_maze(WIDTH, HEIGHT):
    """
    crea una matriz que representa un laberinto vacio.
    cada celda empieza con el valor 15, osea, que tiene las
    paredes levantadas.
    rows: filas del laberinto
    cols: columnas del laberinto
    "_": variable ignorada
    """
    FULL_WALLS = 15
    maze = []
    for _ in range(WIDTH):
        WIDTH = [FULL_WALLS for _ in range(HEIGHT)]
        maze.append(WIDTH)
    return (maze)


maze = create_empty_maze(3, 4)
for row in maze:
    print(row)
