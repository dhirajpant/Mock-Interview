import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import re
import fitz  # PyMuPDF for PDF resume parsing
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("GOOGLE_API_KEY is not set in the environment variables.")
    st.stop()

# Configure the Gemini API for LangChain
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
except Exception as e:
    st.error(f"Failed to initialize language model: {e}")
    st.stop()

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state['questions'] = []
    st.session_state['current_question'] = 0
    st.session_state['responses'] = []
    st.session_state['feedback'] = []
    st.session_state['quit'] = False

# Helper function: Extract text from uploaded PDF
def extract_text_from_pdf(uploaded_file):
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

# App UI
st.title("🧠 AI-Powered Behavioral Mock Interview")
st.write("Start with an introduction and answer behavioral questions one by one. Each question may build on your previous answers.")

# User inputs
job_title = st.text_input("Enter the job title:")
resume_option = st.radio("How would you like to provide your resume?", ["Paste Text", "Upload PDF"])

resume_text = ""
if resume_option == "Paste Text":
    resume_text = st.text_area("Paste your resume text here:")
else:
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")
    if uploaded_file:
        resume_text = extract_text_from_pdf(uploaded_file)

include_job_desc = st.checkbox("Add a job description?")
job_desc = st.text_area("Paste the job description:") if include_job_desc else "Not provided"

# LangChain prompt template for questions
question_prompt = PromptTemplate(
    input_variables=["job_title", "resume", "job_desc", "past_responses"],
    template="""
    You are an AI interviewer conducting a behavioral mock interview for the position of {job_title}.
    The candidate's resume is as follows:
    {resume}

    Job description:
    {job_desc}

    Here are the candidate's previous answers:
    {past_responses}

    Now, ask the next behavioral interview question (1 question only). Start with an introduction question if this is the first.
    """
)
question_chain = LLMChain(llm=llm, prompt=question_prompt)

# LangChain prompt template for feedback
feedback_prompt = PromptTemplate(
    input_variables=["question", "answer"],
    template="""
    You are an expert interview coach. Given the following interview question and candidate's answer, provide constructive feedback focusing on clarity, relevance, depth, and communication.

    Question: {question}
    Answer: {answer}

    Feedback:
    """
)
feedback_chain = LLMChain(llm=llm, prompt=feedback_prompt)

# Start Interview
if st.button("Start Mock Interview"):
    if not job_title.strip() or not resume_text.strip():
        st.warning("Please provide both the job title and your resume.")
    else:
        st.session_state['questions'] = []
        st.session_state['responses'] = []
        st.session_state['feedback'] = []
        st.session_state['current_question'] = 0
        st.session_state['quit'] = False

        try:
            output = question_chain.run(job_title=job_title, resume=resume_text, job_desc=job_desc, past_responses="")
            st.session_state['questions'].append(output.strip())
            st.rerun()
        except Exception as e:
            st.error(f"Error generating question: {e}")
            st.stop()

# Display questions and collect responses
if not st.session_state.get('quit', False) and st.session_state['questions'] and st.session_state['current_question'] < len(st.session_state['questions']):
    idx = st.session_state['current_question']
    question = st.session_state['questions'][idx]
    st.subheader(f"Question {idx + 1}:")
    st.markdown(question)
    user_response = st.text_area("Your answer:", key=f"response_{idx}")

    if st.button("Submit Response"):
        if user_response.strip().lower() in ["quit", "exit"]:
            st.session_state['quit'] = True
        elif user_response.strip():
            st.session_state['responses'].append(user_response.strip())

            try:
                feedback = feedback_chain.run(question=question, answer=user_response.strip())
                st.session_state['feedback'].append(feedback.strip())
            except Exception as e:
                st.session_state['feedback'].append("Feedback generation failed.")
                st.error(f"Error generating feedback: {e}")

            past_responses = "\n\n".join([
                f"Q{i+1}: {st.session_state['questions'][i]}\nA{i+1}: {st.session_state['responses'][i]}"
                for i in range(len(st.session_state['responses']))
            ])

            try:
                next_question = question_chain.run(job_title=job_title, resume=resume_text, job_desc=job_desc, past_responses=past_responses)
                st.session_state['questions'].append(next_question.strip())
                st.session_state['current_question'] += 1
            except Exception as e:
                st.error(f"Error generating next question: {e}")
                st.session_state['quit'] = True
        st.rerun()

# Completion & Summary
if st.session_state.get('quit', False) or st.session_state['questions'] and st.session_state['current_question'] >= len(st.session_state['questions']):
    st.success("✅ Mock interview completed!")
    for i, (q, a, f) in enumerate(zip(st.session_state['questions'], st.session_state['responses'], st.session_state['feedback']), 1):
        st.markdown(f"**Q{i}:** {q}")
        st.markdown(f"**A{i}:** {a}")
        st.markdown(f"**Feedback {i}:** {f}")

    full_log = "\n\n".join([
        f"Q{i}: {q}\nA{i}: {a}\nFeedback: {f}"
        for i, (q, a, f) in enumerate(zip(st.session_state['questions'], st.session_state['responses'], st.session_state['feedback']), 1)
    ])
    st.download_button("Download Full Report", full_log, file_name="interview_behavioral_log.txt")

# Optional: Button to quit the interview early
if st.button("End Interview Early"):
    st.session_state['quit'] = True
    st.rerun()