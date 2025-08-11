from dotenv import load_dotenv

from system_agent.agent import AIAgent


# Load environment variables
load_dotenv()


# Example usage and testing
def main():
    """Main function to run the AI Agent"""
    print("=== AI Agent System ===")
    print("Powered by Google Gemini with LangChain")
    print("Type 'quit', 'exit', or 'bye' to stop")
    print("Type 'memory' to see conversation history")
    print("Type 'clear' to clear conversation memory")
    print("-" * 50)
    
    # Initialize agent
    try:
        agent = AIAgent()
        print("✅ AI Agent initialized successfully!")
        print("\nAvailable capabilities:")
        print("- File operations (read, write, delete, list)")
        print("- Web scraping and link extraction")
        print("- System commands and monitoring")
        print("- Database operations (SQLite)")
        print("- Email sending with attachments")
        print("- Archive creation and extraction")
        print("- Network operations (ping, download)")
        print("- Security operations (hashing, duplicate detection)")
        print("- Task scheduling")
        print("\n" + "=" * 50)
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        return
    
    # Main interaction loop
    while True:
        try:
            user_input = input("\n🤖 You: ").strip()
            
            if not user_input:
                continue

            if user_input.lower() == "memory":
                print("\n" + agent.get_memory_summary())
                continue
            
            if user_input.lower() == 'clear':
                result = agent.clear_memory()
                print(f"🧹 {result}")
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            print("\n🔄 Processing your request...")
            response = agent.run(user_input)
            print(f"\n🤖 Agent: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")


if __name__ == "__main__":
    main()
