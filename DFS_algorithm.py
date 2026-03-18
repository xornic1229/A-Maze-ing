import random

# Logica para la generacion del laberinto y estructura de validacion
"""
=== Constantes necesarias de direccion ===
Representamos las paredes usando un bitmask.
Cada dirección ocupa un bit distinto (1,2,4,8).
Así una celda puede almacenar múltiples paredes en un solo entero.
Esto facilita romper paredes y convertir a hexadecimal.
"""

N = 1
E = 2
S = 4
W = 8

opposite = {
    N: S,
    E: W,
    S: N,
    W: E
}

# Movimientos en la matriz (arriba, abajo, izquierda, derecha)
dirs = {
    N: (-1, 0),
    E: (0, 1),
    S: (1, 0),
    W: (0, -1)
}


def create_empty_maze(WIDTH, HEIGHT):
    """
    crea una matriz que representa un laberinto vacio.
    cada celda empieza con el valor 15, osea, que tiene las
    paredes levantadas.
    "_": variable ignorada
    """
    FULL_WALLS = 15
    maze = []
    for _ in range(HEIGHT):
        row = [FULL_WALLS for _ in range(WIDTH)]
        maze.append(row)
    return (maze)


# AUXILIARES
# Verifica que este dentro del mapa
def in_bounds(r, c, rows, cols):
    if r < 0 or r >= rows:
        return (False)
    elif c < 0 or c >= cols:
        return (False)
    else:
        return (True)


def unvisited_neighbors(r, c, visited, rows, cols):
    neigbors = []
    # Revisar todas las direcciones, dr, dc dice "cómo moverse en la matriz"
    for direction, (dr, dc) in dirs.items():
        # calcular coordenadas, nr y nc es la pocicion del vecino
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc, rows, cols) and (nr, nc) not in visited:
            neigbors.append((nr, nc, direction))  # agregar vecino
    return (neigbors)


# Romper pared y pared vecina
def break_wall(maze, r1, c1, r2, c2, direction):
    # romper pared de celda actual
    maze[r1][c1] &= ~direction
    # romper pared celda vecina
    maze[r2][c2] &= ~opposite[direction]


# Generador DFS
def generate_perfect_maze(rows, cols, entry):
    maze = create_empty_maze(rows, cols)
    visited = set()
    stack = []

    er, ec = entry
    if not in_bounds(er, ec, rows, cols):
        raise ValueError("ENTRY esta fuera de los limites")

    stack.append(entry)
    visited.add(entry)

    while stack:
        # mira el ultimo elemento, en este caso, celda actual
        r, c = stack[-1]
        neighbors = unvisited_neighbors(r, c, visited, rows, cols)
        if neighbors:
            # Elegimos un vecino aleatorio
            nr, nc, direction = random.choice(neighbors)
            break_wall(maze, r, c, nr, nc, direction)
            visited.add((nr, nc))
            stack.append((nr, nc))
        else:
            stack.pop()
    # Matriz modificada con las paredes rotas
    return (maze)


def validate_walls(maze):
    rows = len(maze)
    cols = len(maze[0])

    for r in range(rows):
        for c in range(cols):
            walls = maze[r][c]

            # Si una pared existe en un lado pero no en el otro
            # → inconsistencia → False.
            if r > 0:
                if ((walls & N) > 0) != ((maze[r - 1][c] & S) > 0):
                    return (False)
            if r < rows - 1:
                if ((walls & S) > 0) != ((maze[r + 1][c] & N) > 0):
                    return (False)
            if c > 0:
                if ((walls & W) > 0) != ((maze[r][c - 1] & E) > 0):
                    return (False)
            if c < cols - 1:
                if ((walls & E) > 0) != ((maze[r][c + 1] & W) > 0):
                    return (False)
    return (True)


maze = generate_perfect_maze(4, 4, (0,0))
for row in maze:
    print(row)
print(validate_walls(maze))
