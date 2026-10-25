import streamlit as st
from openai import OpenAI
import httpx

# 1. App Page Configuration
st.set_page_config(page_title="Dynamic OpenRouter Chatbot", page_icon="🤖")
st.title("🤖 Dynamic Free AI Assistant")

# 2. Helper function to fetch available FREE models dynamically from OpenRouter API
@st.cache_data(ttl=3600)  # Caches the list for 1 hour so it's super fast
def get_free_models():
    try:
        response = httpx.get("https://openrouter.ai", timeout=10.0)
        if response.status_code == 200:
            all_models = response.json().get("data", [])
            # Filter out only the models that end with ':free'
            free_models = [m["id"] for m in all_models if m["id"].endswith(":free")]
            return sorted(free_models)
    except Exception:
        pass
    # Fallback list if the API request fails
    return [
        "google/gemini-2.5-flash:free",
        "google/gemini-2.5-pro:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-chat:free"
    ]

# Fetch the active list
available_free_models = get_free_models()

# 3. Sidebar for Configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter OpenRouter API Key", type="password", help="Get a free key from openrouter.ai")
    st.markdown("[Get a Free OpenRouter API Key](https://openrouter.ai)")
    
    # DYNAMIC DROPDOWN: User picks from active free models found right now
    selected_model = st.selectbox(
        "Select Active Free Model",
        options=available_free_models,
        index=0 if "google/gemini-2.5-flash:free" not in available_free_models else available_free_models.index("google/gemini-2.5-flash:free")
    )

# 4. Initialize chat history session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. Display historical chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Handle User Input
if prompt := st.chat_input("What is on your mind?"):
    if not api_key:
        st.info("Please add your OpenRouter API key in the sidebar to continue.")
        st.stop()
        
    # Append and display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 7. Call OpenRouter API & Stream Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            http_client = httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
            
            client = OpenAI(
                base_url="https://openrouter.aiapi/v1",
                api_key=api_key,
                http_client=http_client,
                default_headers={
                    "HTTP-Referer": "http://localhost:8501", 
                    "X-Title": "Local Streamlit Test App"      
                }
            )
            
            # Using the dynamically selected model from the sidebar dropdown
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True
            )
            
            for chunk in response:
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices.delta
                    if hasattr(delta, 'content') and delta.content:
                        full_response += delta.content
                        message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error using {selected_model}: {str(e)}")
