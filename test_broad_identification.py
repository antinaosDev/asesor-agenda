import modules.ai_core as ai_core
import datetime
import json
import os

# --- MOCK CLIENT FOR EMAIL ANALYSIS TEST ---
# Since analyze_emails_ai is hard to test directly due to streamlit deps, 
# we will test the prompt logic directly using a raw completion call similar to the function.

def test_email_prompt_logic():
    print("\n--- TESTING EMAIL PROMPT LOGIC ---")
    mock_email_body = """
    Estimados:
    Informo las siguientes fechas para conocimiento:
    ENERO,MARTES 20 |MARZO,MARTES 03|MAYO,MARTES 05
    """
    
    prompt = ai_core.PROMPT_EMAIL_ANALYSIS.format(current_date="2026-02-04")
    user_content = f"ID: 1 | DE: test@test.com | ASUNTO: Fechas | CUERPO: {mock_email_body}"
    
    client = ai_core._get_groq_client()
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1
        )
        content = completion.choices[0].message.content
        print("Raw Output:", content)
        data = json.loads(ai_core._clean_json_output(content))
        print(f"Events Found: {len(data)}")
        for item in data:
            print(f"- [{item.get('type')}] {item.get('summary')} ({item.get('start_time')})")
            
        if len(data) >= 3:
            print("✅ Email Logic Success: Found multiple events in pipe list.")
        else:
            print("❌ Email Logic Fail: Fewer than 3 events found.")
            
    except Exception as e:
        print(f"Error: {e}")

def test_brain_dump_logic():
    print("\n--- TESTING BRAIN DUMP LOGIC ---")
    # Ambiguous case: "Call Juan tomorrow" -> Should be EVENT now, not TASK
    input_text = "Llamar a Juan mañana para ver lo del contrato"
    
    try:
        result = ai_core.process_brain_dump(input_text)
        print("Input:", input_text)
        print("Result Action:", result.get('action'))
        print("Result Summary:", result.get('summary'))
        
        if result.get('action') == 'create_event':
            print("✅ Brain Dump Success: Converted ambiguous 'tomorrow' to EVENT.")
        else:
            print(f"❌ Brain Dump Fail: Start as {result.get('action')} (Expected create_event)")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_email_prompt_logic()
    test_brain_dump_logic()
