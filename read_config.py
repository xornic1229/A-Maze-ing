def read_config(path):
    """
    Este programa genera un laberinto utilizando los parámetros definidos
    en un archivo de configuración externo. (config.txt)
    Se encarga de:
    - Leer el archivo de configuración pasado por argumento.
    - Validar su contenido.
    - Convertir los valores a los tipos adecuados.
    - Devolver un diccionario listo para que el generador de laberintos lo use.

    Es la capa que prepara y asegura que los parámetros sean correctos
    antes de crear el laberinto.
    """
    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: no se pudo abrir el archivo de configuracion {path}")
        return None

    config_raw = {}

    for line in lines:
        # Quita espacios y saltos de linea
        line = line.strip()
        # ignorar lineas vacias o que empiecen con #
        if line == "":
            continue
        if line.startswith("#"):
            continue

        if "=" not in line:
            print(f"Error: linea invalida en config: '{line}'")
            return None

# Partimos la linea en clave y valor, y lo insertamos en el diccionario
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key == "" or value == "":
            print(f"Error: linea invalida en config: '{line}'")
            return None

        config_raw[key] = value


# validar claves obligatorias
    required_keys = ["WIDTH", "HEIGHT", "ENTRY",
                     "EXIT", "OUTPUT_FILE", "PERFECT"]

    for k in required_keys:
        if k not in config_raw:
            print(f"Error: falta la clave obligatoria {k}")
            return None

        config = {}

        try:
            config["WIDTH"] = int(config_raw["WIDTH"])
            config["HEIGHT"] = int(config_raw["HEIGHT"])
        except ValueError:
            print("Error: WIDHT y HEIGHT deben ser enteros validos")
            return None

        def validate_coord(coord_input, config_key):
            parts = coord_input.split(",")
            if len(parts) != 2:
                print(f"Error: {config_key} debe tener formato x,y")
                return None
            try:
                x = int(parts[0].strip())
                y = int(parts[1].strip())
            except ValueError:
                print(f"Error: {config_key} debe contener solo enteros")
                return None
            return (x, y)

        entry = validate_coord(config_raw["ENTRY"], "ENTRY")
        exit_ = validate_coord(config_raw["EXIT"], "EXIT")

        if entry is None or exit_ is None:
            return None

        config["ENTRY"] = entry
        config["EXIT"] = exit_

        perfect_str = config_raw["PERFECT"]

        if perfect_str == "True":
            config["PERFECT"] = True
        elif perfect_str == "False":
            config["PERFECT"] = False
        else:
            print("Error: PERFECT debe ser 'True' o 'False'")
            return None

        config["OUTPUT_FILE"] = config_raw["OUTPUT_FILE"]
        return (config)


read_config("config.txt")
