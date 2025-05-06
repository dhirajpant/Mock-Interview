import streamlit as st
import google.generativeai as genai
import os
import json
import re
from dotenv import load_dotenv

# ---- Load Environment Variables ----
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    st.error("❌ Google API Key not found. Please check your .env file.")
    st.stop()

# ---- Configure Gemini ----
genai.configure(api_key=google_api_key)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# ---- Session State Initialization ----
if "questions" not in st.session_state:
    st.session_state.questions = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# ---- JSON Cleaning Utility ----
def clean_json_text(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"```(json)?", "", cleaned)
        cleaned = cleaned.strip("` \n")
    return cleaned

# ---- Gemini MCQ Generator ----
def get_mcqs(topic, n=5):
    prompt = (
        f"Generate {n} multiple choice questions on the topic '{topic}'. "
        "Each question should have exactly 4 options labeled A-D and include the correct answer letter only. "
        "Respond in this JSON format: "
        "[{'question': '...', 'options': ['A. ...', 'B. ...', 'C. ...', 'D. ...'], 'answer': 'B'}, ...]"
    )
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        cleaned = clean_json_text(raw)
        return json.loads(cleaned)
    except Exception as e:
        st.error("❌ Gemini returned an unrecognized format. Try a different topic.")
        st.text_area("Debug info", raw, height=200)
        return []

# ---- App Title ----
st.title("🎯 Mock Interview System")

# ---- Question Generation ----
if not st.session_state.questions and not st.session_state.submitted:
    with st.form("setup"):
        # User Inputs
        job_title = st.text_input("📌 Job Title (e.g., Software Engineer)", "Software Engineer")
        experience_level = st.selectbox("📊 Experience Level", ["Junior", "Mid-level", "Senior"])
        skills = st.text_input("🛠️ Primary Skills or Technologies (e.g., Python, AWS, React)", "Python, AWS")
        interview_focus = st.selectbox("🎯 Type of Interview/Focus Area", ["Technical Coding", "System Design", "Behavioral", "Mixed"])
        topic = st.text_input("📚 Topic for MCQs (e.g., Computer Networks)", "Computer Networks")
        num_qs = st.slider("🔢 Number of Questions", 3, 10, 5)
        
        submitted = st.form_submit_button("Generate Questions")
        
        if submitted:
            # Generating questions based on user input
            with st.spinner("Generating questions using Gemini..."):
                prompt = (
                    f"Generate {num_qs} multiple choice questions for a {experience_level} {job_title} "
                    f"with expertise in {skills}. The interview should focus on {interview_focus}. "
                    f"Use the topic '{topic}' and create technical and behavioral questions. "
                    "Each question should have 4 options labeled A-D and include the correct answer letter only. "
                    "Respond in this JSON format: "
                    "[{'question': '...', 'options': ['A. ...', 'B. ...', 'C. ...', 'D. ...'], 'answer': 'B'}, ...]"
                )
                st.session_state.questions = get_mcqs(topic, num_qs)
            st.rerun()

# ---- Display Questions ----
if st.session_state.questions and not st.session_state.submitted:
    st.header("📝 Answer the Questions Below")
    for i, q in enumerate(st.session_state.questions):
        st.write(f"Q{i+1}: {q['question']}")
        st.session_state.user_answers[i] = st.radio(
            f"Select your answer for Q{i+1}",
            options=q["options"],
            key=f"q{i}"
        )
    if st.button("Submit Answers"):
        st.session_state.submitted = True
        st.rerun()

# ---- Display Results ----
if st.session_state.submitted:
    st.header("📊 Your Results")
    correct_count = 0
    feedback_prompts = []

    for i, q in enumerate(st.session_state.questions):
        correct_letter = q["answer"]
        correct_option = next(opt for opt in q["options"] if opt.startswith(correct_letter))
        user_answer = st.session_state.user_answers.get(i, "")
        is_correct = user_answer.startswith(correct_letter)

        if is_correct:
            correct_count += 1
            st.write(f"✅ Q{i+1}: {q['question']}")
            st.write(f"Correct! You chose: {user_answer}")
        else:
            st.write(f"❌ Q{i+1}: {q['question']}")
            st.write(f"Incorrect. You chose: {user_answer}. Correct: {correct_option}")
            feedback_prompts.append(f"Q: {q['question']}\nCorrect Answer: {correct_option}\nExplain why.")

    st.success(f"🎯 Final Score: {correct_count} / {len(st.session_state.questions)}")

    if feedback_prompts and st.button("🧠 Show Explanations"):
        with st.spinner("Generating feedback..."):
            explanation_prompt = "\n\n".join(feedback_prompts)
            explanation = model.generate_content(explanation_prompt)
            st.subheader("📘 Detailed Explanation")
            st.write(explanation.text)

    if st.button("🔁 Try Again"):
        st.session_state.clear()
        st.rerun()
