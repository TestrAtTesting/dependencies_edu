import sys
import os
import urllib.request##для сетевых запросов
import urllib.error##и обработки их ошибок
import gzip##для распаровки сжатых пакетов
import io##для работы с потоками в памяти
import re##для обработки символов в парсере

class Config:
    def __init__(self):
        self.package_name = ""
        self.repository_url = ""
        self.test_repo_mode = False
        self.package_version = ""
        self.output_filename = ""
        self.max_depth = 0
        self.filter_substring = ""

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

def parse_depends_line(depends_line):##парсер строки зависимостей
    dependencies = []
    
    if not depends_line:
        return dependencies
    
    ##разделяем по запятым
    parts = depends_line.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        ##обрабатываем альтернативы (разделенные |)
        alternatives = part.split('|')
        for alt in alternatives: ##убираем лишние символы
            alt = alt.strip()
            alt = re.sub(r'\([^)]*\)', '', alt).strip()
            alt = re.sub(r'\s+', ' ', alt).strip()
            
            if alt and alt not in dependencies:
                dependencies.append(alt)
    
    return dependencies

def find_package_dependencies(packages_content, package_name, package_version):##ищет зависимости пакета нужной версии
    lines = packages_content.split('\n')
    current_package = None
    current_version = None
    found_package = False
    dependencies = []
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('Package:'):
            current_package = line.split(':', 1)[1].strip()
            current_version = None
        ##проверяем совпадение версии
        elif line.startswith('Version:') and current_package == package_name:
            current_version = line.split(':', 1)[1].strip()
            if package_version in current_version:
                found_package = True
        
        elif line.startswith('Depends:') and found_package:
            depends_line = line.split(':', 1)[1].strip()
            dependencies = parse_depends_line(depends_line)
            break
    ##обработка ошибок
    if not found_package:
        raise Exception(f"Package {package_name} version {package_version} not found in repository")
    
    return dependencies

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

def get_packages_content(repository_url, test_repo_mode):##получает содержимое пакета
    if test_repo_mode:
        ##работаем в локальном режиме при тестировании
        if os.path.isfile(repository_url):
            #случай с полным путем файла
            if repository_url.endswith('.gz'):
                with gzip.open(repository_url, 'rt', encoding='utf-8') as f:
                    return f.read()
            else:
                with open(repository_url, 'r', encoding='utf-8') as f:
                    return f.read()
        else:
            ##случай с директорией
            packages_path = os.path.join(repository_url, "Packages")
            packages_gz_path = os.path.join(repository_url, "Packages.gz")
            
            if os.path.exists(packages_path):
                with open(packages_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif os.path.exists(packages_gz_path):
                with gzip.open(packages_gz_path, 'rt', encoding='utf-8') as f:
                    return f.read()
            else:
                raise Exception(f"Packages file not found in {repository_url}")
    else:
        ##работаем путем скачивания репозитория
        try:
            ##более общий URL для репозитория Ubuntu
            if not repository_url.endswith('/Packages.gz'):
                if repository_url.endswith('/'):
                    packages_url = repository_url + "dists/focal/main/binary-amd64/Packages.gz"
                else:
                    packages_url = repository_url + "/dists/focal/main/binary-amd64/Packages.gz"
            
            with urllib.request.urlopen(packages_url) as response:
                compressed_data = response.read()
            
            with gzip.open(io.BytesIO(compressed_data), 'rt', encoding='utf-8') as f:
                return f.read()
        except urllib.error.URLError as e:
            raise Exception(f"Error downloading Packages file: {e}")
        except Exception as e:
            raise Exception(f"Error processing Packages file: {e}")

def main():
    ##
    if len(sys.argv) > 1:
        config_name = sys.argv[1]
    else:
        config_name = "C:\conf\config.toml"
    
    print(f"Using config file: {config_name}")
    
    try:
        config = load_config(config_name)
        
        ##получаем содержимое пакетов для определения доступных версий
        packages_content = get_packages_content(
            config.repository_url,
            config.test_repo_mode
        )
        
        ##при отсутствии версии
        if not config.package_version:
            config.package_version = get_latest_package_version(
                packages_content, 
                config.package_name
            )
            print(f"Using latest version: {config.package_version}")
        
        ##получаем зависимости для выбранной версии
        dependencies = find_package_dependencies(
            packages_content,
            config.package_name, 
            config.package_version
        )
        
        ##вывод
        print("Dependencies of package {} version {}:".format(
            config.package_name, config.package_version))
        for dep in dependencies:
            print(f"  - {dep}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
