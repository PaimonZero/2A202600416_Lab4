import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from pydantic import SecretStr
from tools import search_flights, search_hotels, calculate_budget
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

# 1. Read system prompt from file
with open("system_prompt.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read()
    
# 2. Declare State
class AgentState(TypedDict):
    """
    Type mapping for internal graph state.
    'messages' will be updated by adding new messages to the existing list.
    """
    messages: Annotated[list, add_messages]
    
# 3. Initialize Model and Tools
def get_model() -> ChatOpenAI:
    """
    Setup LangChain OpenAI model instance.
    Prioritize GitHub PAT for authentication, then fallback to OpenAI key.
    """
    github_pat = os.getenv("GITHUB_PAT")
    if github_pat:
        print("--- Using GitHub PAT ---")
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=SecretStr(github_pat),
            base_url="https://models.inference.ai.azure.com"
        )
    print("--- Falling back to OpenAI API ---")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(
        model="gpt-4o",
        api_key=SecretStr(openai_api_key) if openai_api_key else None
    )

llm = get_model()
tools_list = [search_flights, search_hotels, calculate_budget]

# Bind tools to our LLM enabling it to intelligently call tools
llm_with_tools = llm.bind_tools(tools_list)

# 4. Define Agent Node
def agent_node(state: AgentState) -> dict:
    """
    The core agent node logic. 
    Injects system prompt at the beginning if not already present.
    """
    messages = state["messages"]
    
    # Prepend the system prompt for robust instructions
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=system_prompt)] + messages
        
    try:
        response = llm_with_tools.invoke(messages)
        
        # Logging details for observability
        if response.tool_calls:
            for tc in response.tool_calls:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", None)
                print(f"[Tool Call] {name} with args {args}")
        else:
            print("[No Tool Call] Agent response without tool usage \n")
            
        return {"messages": [response]}
    except Exception as error:
        # Fallback mechanism if the model call completely fails
        print(f"[Error] Failed to invoke LLM: {error}")
        return {"messages": [{"role": "assistant", "content": "Rất tiếc, đã xảy ra lỗi trong hệ thống của TravelBuddy."}]}

# 5. Build State Graph (Nodes & Edges setup)
builder = StateGraph(AgentState)

# Add nodes to our agentic graph
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools_list))

# Define flow of edges
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")  # Always return to the agent after executing a tool so it can summarize

# Compile the final executable graph
graph = builder.compile()

# 6. Chat loop
if __name__ == "__main__":
    print("=" * 60)
    print("TravelBuddy — Trợ lý Du lịch Thông minh")
    print(" Gõ 'quit' để thoát")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\nBạn: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break
            
            print("\nTravelBuddy đang suy nghĩ...")
            
            # Start our LangGraph execution
            result = graph.invoke({"messages": [("human", user_input)]})
            
            # Retrieve and print final response from our message trace
            final = result["messages"][-1]
            print(f"\nTravelBuddy: {final.content}")
        
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nTạm biệt!")
            break
        except Exception as error:
            print(f"\n[Error] Chat loop exception: {error}")