import sys
import os

class Config:
    def __init__(self):
        self.package_name = ""
        self.repository_url = ""
        self.test_repo_mode = False
        self.package_version = ""
        self.output_filename = ""
        self.max_depth = 0
        self.filter_substring = ""

    def display_parameters(self):
        print("package_name:", self.package_name)
        print("repository_url:", self.repository_url)
        print("test_repo_mode:", self.test_repo_mode)
        print("package_version:", self.package_version)
        print("output_filename:", self.output_filename)
        print("max_depth:", self.max_depth)
        print("filter_substring:", self.filter_substring)

def parse_toml_value(value_str):##кастомный парсер .toml раз уж нельзя использовать сторонние библиотеки
    value_str = value_str.strip()
    
    ##булевы значения
    if value_str.lower() == "true":
        return True
    elif value_str.lower() == "false":
        return False
    
    ##числа
    if value_str.isdigit() or (value_str[0] == '-' and value_str[1:].isdigit()):
        return int(value_str)
    
    ##строки (убираем кавычки если есть)
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]
    
    ##строка без кавычек
    return value_str

def load_config(filename):
    config = Config()
    ##попытка загрузить конфигурацию
    try:
        if not os.path.exists(filename):
            raise Exception(f"Config file '{filename}' not found")
        
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        raise Exception(f"Error reading config file: {e}")
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        ##пропуск комментариев и пустых строк
        if not line or line.startswith('#'):
            continue
        
        ##проверка на синтаксис
        if '=' not in line:
            raise Exception(f"Invalid TOML syntax at line {line_num}: no '=' found")
        
        key, value = line.split('=', 1)
        key = key.strip()
        value = parse_toml_value(value)
        
        ##установка значений в конфигурацию и проверка на неверные параметры
        try:
            if key == "package_name":
                config.package_name = str(value)
            elif key == "repository_url":
                config.repository_url = str(value)
            elif key == "test_repo_mode":
                config.test_repo_mode = bool(value)
            elif key == "package_version":
                config.package_version = str(value)
            elif key == "output_filename":
                config.output_filename = str(value)
            elif key == "max_depth":
                config.max_depth = int(value)
            elif key == "filter_substring":
                config.filter_substring = str(value)
            else:
                raise Exception(f"Unknown config parameter: {key}")
        except (ValueError, TypeError) as e:
            raise Exception(f"Invalid value for parameter '{key}' at line {line_num}: {e}")
    
    ##проверка на корректность и наличие параметров
    required_params = [
        ("package_name", config.package_name),
        ("repository_url", config.repository_url),
        ("package_version", config.package_version),
        ("output_filename", config.output_filename),
        ("filter_substring", config.filter_substring)
    ]
    
    for param_name, param_value in required_params:##наличие
        if not param_value:
            raise Exception(f"Required parameter '{param_name}' is missing or empty")
    
    if config.max_depth <= 0:##корректность
        raise Exception("Parameter 'max_depth' must be positive integer")
    
    return config

def main():
    config_name = str(input("config_name = "))
    try:
        config = load_config(config_name)
        config.display_parameters()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
