
from dotenv import load_dotenv
import os
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import pandas as pd




# Load from .env file
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')

def extract_text_line_by_line(text):
    """
    Process text line by line to extract and store it.
    :param text: Text to process.
    :return: Processed text line by line.
    """
    lines = text.splitlines()
    processed_lines = "\n".join(line.strip() for line in lines if line.strip())
    return processed_lines

def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR.
    :param image_path: Path to the image file.
    :return: Extracted text line by line.
    """
    try:
        with Image.open(image_path) as img:
            raw_text = pytesseract.image_to_string(img)
            lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
            structured_text = "\n".join(lines)
            return structured_text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""

def extract_text_from_pdf(pdf_path, output_folder):
    """
    Extract text from a PDF, including flattening it if necessary.
    :param pdf_path: Path to the PDF file.
    :param output_folder: Folder to store intermediate images if needed.
    :return: Extracted text line by line.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"

        if not text.strip():
            images = convert_from_path(pdf_path)
            for i, img in enumerate(images):
                img_path = os.path.join(output_folder, f"page_{i + 1}.png")
                img.save(img_path, "PNG")
                raw_text = extract_text_from_image(img_path)
                text += raw_text + "\n"

        return extract_text_line_by_line(text)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""





def answer_queries_from_file_with_prompt(file_path, excel_path, output_column="Answer"):
    """
    Answer multiple queries using a text file as the knowledge base with FAISS, OpenAI, and LangChain.

    Args:1q
        file_path (str): Path to the text file.
        excel_path (str): Path to the Excel file containing the queries.
        output_column (str): The column name to store answers in the Excel sheet.

    Returns:
        None: Saves the answers back to the Excel file.
    """
    # Step 1: Load and chunk the text file
    loader = TextLoader(file_path, encoding='utf-8')  # Specify the encoding
    documents = loader.load()

    # Step 2: Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    # Step 3: Create a vector database with FAISS
    # Explicitly configure OpenAI embeddings without proxies
    embeddings = OpenAIEmbeddings(
        openai_api_key=openai_api_key
    )
    vector_store = FAISS.from_documents(docs, embeddings)

    # Step 4: Define a prompt template for concise answers
    prompt_template = """
    "You are a highly precise and concise assistant. "
    "Answer the following question based, and return the exact and concise response without any additional explanation., dont repeat the question in answer "

    Context: {context}
    Query: {query}
    Answer:
    """
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "query"])

    # Step 5: Initialize the ChatOpenAI model and LLMChain
    chat_model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)  # Use the chat model
    chain = LLMChain(llm=chat_model, prompt=prompt)

    # Step 6: Read questions from the Excel file
    df = pd.read_excel(excel_path)
    if "Query" not in df.columns:
        raise ValueError("The Excel file must contain a 'Query' column.")

    queries = df["Query"].tolist()

    # Step 7: Process each query and store the answers
    answers = []
    retriever = vector_store.as_retriever()
    for query in queries:
        # Retrieve relevant documents for the current query
        relevant_docs = retriever.get_relevant_documents(query)

        # Combine the retrieved documents into a single context
        context = "\n\n".join([doc.page_content for doc in relevant_docs])

        # Run the chain with the current query and context
        answer = chain.run({"context": context, "query": query})
        answers.append(answer)

    # Step 8: Save answers to the Excel file
    df[output_column] = answers
    df.to_excel(excel_path, index=False)

    print(f"Answers saved to column '{output_column}' in the Excel file.")


