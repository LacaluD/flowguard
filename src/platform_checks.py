# import shutil
# from pathlib import Path
# import sys

# def find_executable(filename, extra_paths=None):
#     """Ищем бинарник сначала в PATH, потом в дополнительных папках (не рекурсивно)."""
#     # 1. PATH
#     path = shutil.which(filename)
#     if path:
#         return Path(path)

#     # 2. Дополнительные папки
#     default_dirs = []
#     if sys.platform == "win32":
#         default_dirs = [Path("C:/")]    # , Path("C:/Tools")
#     else:
#         default_dirs = [Path("/usr/local/bin"), Path("/usr/bin"), Path("/opt/homebrew/bin"), Path("/usr/local/sbin")]

#     if extra_paths:
#         default_dirs += [Path(p) for p in extra_paths]

#     # 3. Проверяем существование файла в этих папках
#     for d in default_dirs:
#         candidate = d / filename
#         if candidate.exists():
#             return candidate

#     return None

# def find_executable_recursive(filename, search_dir):
#     """Рекурсивный поиск исполняемого файла в папке search_dir"""
#     search_dir = Path(search_dir)
#     if not search_dir.exists():
#         return None
#     for path in search_dir.rglob(filename):
#         if path.exists():
#             return path
#     return None

# # 🔹 Пример использования
# yq_filename = "yq.exe" if sys.platform == "win32" else "yq"
# yml2_filename = "yml2dot.exe" if sys.platform == "win32" else "yml2dot"

# # сначала обычный поиск
# yq_exe = find_executable(yq_filename)
# yml2_dot_exe = find_executable(yml2_filename)

# # если не нашли — рекурсивно в C:/Progs
# if not yq_exe:
#     yq_exe = find_executable_recursive(yq_filename, "C:/Progs")
# if not yml2_dot_exe:
#     yml2_dot_exe = find_executable_recursive(yml2_filename, "C:/Progs")

# if not yq_exe or not yml2_dot_exe:
#     print("❌ Не найдены все необходимые исполняемые файлы:")
#     print("yq:", yq_exe)
#     print("yml2dot:", yml2_dot_exe)
#     sys.exit(1)

# print("✅ Найдены все исполняемые файлы:")
# print("yq:", yq_exe)
# print("yml2dot:", yml2_dot_exe)



import shutil
from pathlib import Path
import sys

def find_executable(filename, extra_paths=None):
    """Ищем бинарник сначала в PATH, потом в дополнительных папках (не рекурсивно)."""
    # 1. PATH
    path = shutil.which(filename)
    if path:
        return Path(path)

    # 2. Дополнительные папки
    default_dirs = []
    if sys.platform == "win32":
        default_dirs = [Path("C:/")]    # , Path("C:/Tools")
    else:
        default_dirs = [Path("/usr/local/bin"), Path("/usr/bin"), Path("/opt/homebrew/bin"), Path("/usr/local/sbin")]

    if extra_paths:
        default_dirs += [Path(p) for p in extra_paths]

    # 3. Проверяем существование файла в этих папках
    for d in default_dirs:
        candidate = d / filename
        if candidate.exists():
            return candidate

    return None

def find_executable_recursive(filename, search_dir):
    """Рекурсивный поиск исполняемого файла в папке search_dir"""
    search_dir = Path(search_dir)
    if not search_dir.exists():
        return None
    for path in search_dir.rglob(filename):
        if path.exists():
            return path
    return None

# 🔹 Пример использования
yq_filename = "yq.exe" if sys.platform == "win32" else "yq"
yml2_filename = "yml2dot.exe" if sys.platform == "win32" else "yml2dot"

# сначала обычный поиск
yq_exe = find_executable(yq_filename)
yml2_dot_exe = find_executable(yml2_filename)

# если не нашли — рекурсивно в C:/Progs
if not yq_exe:
    yq_exe = find_executable_recursive(yq_filename, "C:/Progs")
if not yml2_dot_exe:
    yml2_dot_exe = find_executable_recursive(yml2_filename, "C:/Progs")

if not yq_exe or not yml2_dot_exe:
    print("❌ Не найдены все необходимые исполняемые файлы:")
    print("yq:", yq_exe)
    print("yml2dot:", yml2_dot_exe)
    sys.exit(1)

print("✅ Найдены все исполняемые файлы:")
print("yq:", yq_exe)
print("yml2dot:", yml2_dot_exe)
