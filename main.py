import os
from dotenv import load_dotenv
from system_agent.agent import AIAgent


# Load environment variables
load_dotenv()


# Example usage and testing
def main():
    """Main function to run the AI agent"""
    # Initialize the agent (you need to provide your Google API key)
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ Please set your GOOGLE_API_KEY environment variable")
        print("You can get your API key from: https://makersuite.google.com/app/apikey")
        return
    
    print("🔄 Initializing AI Agent with Google Gemini...")
    
    try:
        agent = AIAgent(google_api_key, "gemini-2.5-flash-lite")
        print("✅ AI Agent initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing agent: {str(e)}")
        return
    
    print("\n" + "="*60)
    print("🤖 AI AGENT WITH GOOGLE GEMINI")
    print("="*60)
    print(agent.get_capabilities())
    print("\n📝 SPECIAL COMMANDS:")
    print("   • Type 'quit' or 'exit' to stop")
    print("   • Type 'memory' to see conversation history") 
    print("   • Type 'clear' to clear memory")
    print("   • Type 'help' to see capabilities again")
    print("="*60)
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("\n👋 Goodbye! Thanks for using the AI Agent.")
                break
            elif user_input.lower() == 'memory':
                print("\n" + agent.get_memory_summary())
                continue
            elif user_input.lower() == 'clear':
                print("\n" + agent.clear_memory())
                continue
            elif user_input.lower() == 'help':
                print(agent.get_capabilities())
                continue
            elif not user_input:
                continue
            
            print("\n🤖 AI Agent: ", end="")
            response = agent.chat(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! (Interrupted by user)")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            print("Please try again or type 'quit' to exit.")

if __name__ == "__main__":
    main()
