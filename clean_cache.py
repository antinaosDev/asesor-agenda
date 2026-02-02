"""
Script para limpiar caché de Python y forzar recarga
"""
import os
import shutil
import sys

print("="*60)
print("LIMPIANDO CACHÉ DE PYTHON")
print("="*60)

# Eliminar archivos .pyc y carpetas __pycache__
deleted_count = 0
for root, dirs, files in os.walk('.'):
    # Eliminar carpetas __pycache__
    if '__pycache__' in dirs:
        pycache_path = os.path.join(root, '__pycache__')
        try:
            shutil.rmtree(pycache_path)
            print(f"✅ Eliminado: {pycache_path}")
            deleted_count += 1
        except Exception as e:
            print(f"❌ Error eliminando {pycache_path}: {e}")
    
    # Eliminar archivos .pyc
    for file in files:
        if file.endswith('.pyc'):
            pyc_path = os.path.join(root, file)
            try:
                os.remove(pyc_path)
                print(f"✅ Eliminado: {pyc_path}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error eliminando {pyc_path}: {e}")

print(f"\n🗑️ Total de archivos/carpetas eliminados: {deleted_count}")

print("\n" + "="*60)
print("INSTRUCCIONES FINALES")
print("="*60)
print("""
✅ Caché limpiado exitosamente

🔄 AHORA DEBES:

1. Si estás usando STREAMLIT LOCAL:
   - Detén la app (Ctrl+C)
   - Ejecuta: streamlit run app.py
   
2. Si estás usando STREAMLIT CLOUD:
   - Ve a: https://share.streamlit.io
   - Encuentra tu app "asesor-agenda"
   - Click en ⋮ → "Reboot app"
   - Espera 1-2 minutos

3. Luego RECARGA la página en tu navegador (F5 o Ctrl+R)

⚠️ Si después de esto SIGUE apareciendo el JSON:
   - Presiona Ctrl+Shift+R (recarga dura del navegador)
   - O abre en ventana privada/incógnito
""")
