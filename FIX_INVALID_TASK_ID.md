# 🔧 Fix: Error "Invalid Task ID" en Optimización de Agenda

## ❌ Problema Detectado

Al usar la función **"Optimizar Agenda con IA"**, se generaban múltiples errores:

```
Error updating task: <HttpError 400 when requesting 
https://tasks.googleapis.com/tasks/v1/lists/.../tasks/task_id_1?alt=json 
returned "Invalid task ID". Details: "[{'message': 'Invalid task ID', 
'domain': 'global', 'reason': 'invalid'}]">
```

### 🔍 Causa Raíz

La IA estaba generando **IDs ficticios** (`task_id_1`, `task_id_2`, `event_id_1`, etc.) en su plan de optimización, en lugar de usar los **IDs reales** de Google Calendar y Google Tasks que se le proporcionaban en el input.

## ✅ Solución Implementada

### Archivo Modificado
- **`modules/ai_core.py`** - Función `_call_agenda_ai_chunk()`

### Cambios Realizados

1. **Expandido la lista de colores válidos** para que la IA tenga contexto completo
2. **Agregado regla crítica** "CRITICAL RULE - USE REAL IDs":
   - La IA DEBE usar los IDs exactos del input
   - NO generar IDs ficticios como `event_id_1`
   - SOLO incluir items que realmente necesitan optimización
   - OMITIR items ya bien escritos

3. **Agregado ejemplo concreto** mostrando:
   - Input de ejemplo con ID real: `"abc123xyz"`
   - Output correcto usando ese mismo ID

### Mejoras Adicionales

- ✅ Reducción de procesamiento innecesario (solo optimiza lo que necesita cambios)
- ✅ Colores completos (1-11) para mejor categorización
- ✅ Instrucciones más claras y explícitas para la IA

## 📊 Resultado Esperado

### ❌ Antes (Incorrecto):
```json
{
  "optimization_plan": {
    "task_id_1": {"type": "task", "new_title": "..."},
    "task_id_2": {"type": "task", "new_title": "..."}
  }
}
```

### ✅ Ahora (Correcto):
```json
{
  "optimization_plan": {
    "MDA4MTk1NzEzOTIxNDE3MzcyOTI6MDow": {
      "type": "task", 
      "new_title": "Completar informe trimestral"
    },
    "abc123xyz_real_event_id": {
      "type": "event",
      "new_summary": "Reunión Estratégica del Equipo",
      "colorId": "4"
    }
  }
}
```

## 🚀 Próximos Pasos

1. **Probar la optimización** con eventos y tareas reales
2. **Verificar** que no se generen más errores de "Invalid Task ID"
3. **Confirmar** que solo se optimizan items que realmente lo necesitan

---

**Desarrollado por**: Antigravity AI Assistant  
**Fecha**: 30 de Enero, 2026 - 02:05 AM  
**Commit**: `d09d0a7` - Fix: IDs inválidos en optimización de agenda
