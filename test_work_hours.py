import modules.ai_core as ai_core
import datetime

print("--- TESTING WORK HOUR LIMITS ---")

def test_time(input_time, label):
    print(f"\nEvaluating: {label} ({input_time})")
    calc = ai_core._calculate_default_end_time(input_time)
    
    start_dt = datetime.datetime.fromisoformat(input_time)
    end_dt = datetime.datetime.fromisoformat(calc)
    
    duration = (end_dt - start_dt).total_seconds() / 3600
    end_hour = end_dt.hour + end_dt.minute/60.0
    
    print(f"-> Calculated End: {calc}")
    print(f"-> Duration: {duration:.2f}h")
    print(f"-> End Hour: {end_hour:.2f}")
    return duration, end_hour

# 1. Mon-Thu Normal Case (14:30 -> 16:30)
# Monday Feb 2nd 2026
d, h = test_time("2026-02-02T14:30:00", "Monday Normal")
if abs(d - 2.0) < 0.1: print("✅ OK")
else: print("❌ FAIL")

# 2. Mon-Thu Limit Case (15:30 -> Should be 17:00, i.e. 1.5h)
d, h = test_time("2026-02-02T15:30:00", "Monday Cap")
if abs(h - 17.0) < 0.1 and abs(d - 1.5) < 0.1: print("✅ OK (Capped at 17:00)")
else: print(f"❌ FAIL (Expected 17.0 end, got {h})")

# 3. Friday Limit Case (14:30 -> Should be 16:00, i.e. 1.5h)
# Friday Feb 6th 2026
d, h = test_time("2026-02-06T14:30:00", "Friday Cap")
if abs(h - 16.0) < 0.1 and abs(d - 1.5) < 0.1: print("✅ OK (Capped at 16:00)")
else: print(f"❌ FAIL (Expected 16.0 end, got {h})")

# 4. Late Start Case (18:00 -> Should keep 2h, i.e. 20:00)
# Monday Feb 2nd 2026
d, h = test_time("2026-02-02T18:00:00", "Monday Late Start")
if abs(d - 2.0) < 0.1: print("✅ OK (Kept 2h for late start)")
else: print("❌ FAIL")
