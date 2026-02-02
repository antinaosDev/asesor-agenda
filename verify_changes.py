"""
Script para verificar que los cambios se han aplicado correctamente
"""

print("="*60)
print("VERIFICANDO MÓDULO chat_view.py")
print("="*60)

# Importar el módulo
import sys
sys.path.insert(0, 'modules')
import chat_view

# Leer el archivo
with open('modules/chat_view.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificaciones
checks = {
    "✅ JSON cleaning code exists": "# Clean JSON from display" in content,
    "✅ display_text variable exists": "display_text = full_response" in content,
    "✅ regex strategies defined": "regex_strategies = [" in content,
    "✅ datetime.datetime.fromisoformat": "datetime.datetime.fromisoformat" in content,
    "✅ Auto-generate end_time comment": "# Auto-generate end_time if missing" in content,
}

print("\nEstado del código:")
for check, result in checks.items():
    status = "✅" if result else "❌"
    print(f"{status} {check.replace('✅ ', '')}")

# Verificar si hay errores de sintaxis
print("\n" + "="*60)
print("VERIFICANDO SINTAXIS")
print("="*60)

try:
    import py_compile
    py_compile.compile('modules/chat_view.py', doraise=True)
    print("✅ No hay errores de sintaxis")
except SyntaxError as e:
    print(f"❌ ERROR DE SINTAXIS: {e}")

print("\n" + "="*60)
print("CONCLUSIÓN")
print("="*60)

if all(checks.values()):
    print("✅ TODOS LOS CAMBIOS ESTÁN EN EL ARCHIVO")
    print("\n🔄 SI LA APP NO FUNCIONA, NECESITAS:")
    print("   1. Subir los cambios: git add . && git commit -m 'fix' && git push")
    print("   2. REINICIAR la aplicación Streamlit completamente")
    print("   3. Si es Streamlit Cloud: Reboot app desde el dashboard")
else:
    print("❌ FALTAN ALGUNOS CAMBIOS EN EL ARCHIVO")
    print("   Puede que el archivo no se haya guardado correctamente")
