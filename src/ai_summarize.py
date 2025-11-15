from langchain_openai import OpenAI
from langchain.agents import create_pandas_dataframe_agent
from dotenv import load_dotenv
import os

load_dotenv()
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_dataframe(df, query):
    agent = create_pandas_dataframe_agent(llm, df)
    return agent.run(query)

# Example: summarize_dataframe(parsed_df, "Summarize revenue trends for financial analysis")
