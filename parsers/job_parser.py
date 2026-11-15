# parsers/job_parser.py
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from schemas.job_schema import JobPosting

load_dotenv()


def get_llm():
    """Initializes the LLM based on environment variables."""
    if os.getenv("GEMINI_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    else:
        raise ValueError("Missing GEMINI_API_KEY or OPENAI_API_KEY in .env file.")


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert technical talent researcher. Your job is to extract and "
            "normalize job description details into a strictly structured schema. "
            "Do not hallucinate skills or requirements not present in the text.",
        ),
        (
            "human",
            "Extract the job posting details from the raw page content below:\n\n{raw_text}",
        ),
    ]
)


async def parse_job_description(raw_text: str) -> JobPosting:
    """Takes unformatted scraped text and returns a validated JobPosting instance."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(JobPosting)
    extraction_chain = EXTRACTION_PROMPT | structured_llm
    
    parsed_job: JobPosting = await extraction_chain.ainvoke({"raw_text": raw_text})
    return parsed_job