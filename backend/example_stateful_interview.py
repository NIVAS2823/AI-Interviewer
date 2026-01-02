"""
Example: How to use the Stateful Question Agent
This shows the complete flow with memory and follow-ups
"""
import asyncio
from app.services.orchestration.interview_state import InterviewStateManager
from app.services.orchestration.stateful_question_agent import StatefulQuestionAgent


async def example_stateful_interview():
    """
    Example showing how stateful agent remembers and generates follow-ups
    """
    
    # Initialize agent
    agent = StatefulQuestionAgent()
    state_manager = InterviewStateManager()
    
    # Create initial state
    state = state_manager.create_initial_state(
        interview_id="test_123",
        interview_type="technical",
        difficulty="medium",
        max_questions=5,
        candidate_name="John Doe",
        candidate_skills=["Python", "React", "AWS", "Docker"],
        job_description="Senior Full Stack Developer position requiring Python, React, and cloud experience.",
    )
    
    print("=== STATEFUL INTERVIEW SIMULATION ===\n")
    
    # =============================================
    # Question 1: Opening
    # =============================================
    print("--- Generating Question 1 ---")
    question1, state = await agent.generate_next_question_stateful(state)
    print(f"Q1: {question1.question_text}\n")
    
    # Candidate answers
    answer1 = (
        "I have 5 years of Python experience, mostly building web APIs with Django and Flask. "
        "I've also worked extensively with React for the frontend. "
        "However, I'm still learning AWS - I've only used EC2 and S3 so far."
    )
    print(f"Candidate: {answer1}\n")
    
    # ✅ MEMORY: Extract insights from answer
    state = await agent.process_answer_and_extract_insights(state, answer1)
    
    print("🧠 Agent Memory Updated:")
    print(f"   - Insights extracted: {len(state.memory.candidate_insights)}")
    print(f"   - Topics to explore: {state.memory.topics_to_explore}")
    print(f"   - Reasoning: {state.memory.reasoning_history[-1]}\n")
    
    # =============================================
    # Question 2: Should be a FOLLOW-UP on AWS
    # =============================================
    print("--- Generating Question 2 (Expected: Follow-up on AWS) ---")
    question2, state = await agent.generate_next_question_stateful(state)
    print(f"Q2: {question2.question_text}")
    print(f"   ✅ Is this about AWS? Check if it digs deeper!\n")
    
    # Candidate answers about AWS
    answer2 = (
        "Yes, so I used AWS mostly for simple deployments. "
        "I set up EC2 instances manually and used S3 for file storage. "
        "I haven't worked with Lambda, ECS, or other advanced services yet. "
        "I'm comfortable with Docker though - I containerize all my apps."
    )
    print(f"Candidate: {answer2}\n")
    
    # ✅ MEMORY: Extract more insights
    state = await agent.process_answer_and_extract_insights(state, answer2)
    
    print("🧠 Agent Memory Updated:")
    print(f"   - New insights: {state.memory.candidate_insights[-1].topic}")
    print(f"   - Topics to explore: {state.memory.topics_to_explore}")
    print(f"   - Reasoning: {state.memory.reasoning_history[-1]}\n")
    
    # =============================================
    # Question 3: Should follow up on Docker
    # =============================================
    print("--- Generating Question 3 (Expected: Follow-up on Docker) ---")
    question3, state = await agent.generate_next_question_stateful(state)
    print(f"Q3: {question3.question_text}")
    print(f"   ✅ Does this explore Docker/containerization?\n")
    
    # Candidate answers
    answer3 = (
        "I use Docker for all my projects. I write Dockerfiles, use docker-compose for multi-container apps, "
        "and have experience with Docker networking and volumes. "
        "I've also deployed containers to production using Docker Swarm."
    )
    print(f"Candidate: {answer3}\n")
    
    state = await agent.process_answer_and_extract_insights(state, answer3)
    
    print("🧠 Agent Memory Updated:")
    print(f"   - Covered topics: {state.memory.covered_topics}")
    print(f"   - Reasoning: {state.memory.reasoning_history[-1]}\n")
    
    # =============================================
    # Question 4: New topic (not follow-up)
    # =============================================
    print("--- Generating Question 4 (Expected: New topic) ---")
    question4, state = await agent.generate_next_question_stateful(state)
    print(f"Q4: {question4.question_text}\n")
    
    # Final answer
    answer4 = "I focus on clean code, test-driven development, and good documentation."
    print(f"Candidate: {answer4}\n")
    
    state = await agent.process_answer_and_extract_insights(state, answer4)
    
    # =============================================
    # Question 5: Closing
    # =============================================
    print("--- Generating Question 5 (Expected: Closing question) ---")
    question5, state = await agent.generate_next_question_stateful(state)
    print(f"Q5: {question5.question_text}\n")
    
    # =============================================
    # Show final memory state
    # =============================================
    print("\n=== FINAL AGENT MEMORY ===")
    print(f"Topics covered: {state.memory.covered_topics}")
    print(f"Total insights extracted: {len(state.memory.candidate_insights)}")
    print(f"Reasoning history ({len(state.memory.reasoning_history)} entries):")
    for i, r in enumerate(state.memory.reasoning_history, 1):
        print(f"  {i}. {r}")
    
    print("\n✅ Interview completed with full memory and intelligent follow-ups!")


async def comparison_without_memory():
    """
    Show the difference WITHOUT stateful memory (current implementation)
    """
    print("\n\n=== WITHOUT MEMORY (Current Implementation) ===\n")
    
    questions = [
        "Tell me about your background.",
        "What's your experience with Python?",  # ❌ Generic, no follow-up
        "Tell me about React.",                  # ❌ Doesn't follow up on AWS weakness
        "What cloud services do you know?",      # ❌ Repeating cloud topic
        "Any questions for us?",
    ]
    
    for i, q in enumerate(questions, 1):
        print(f"Q{i}: {q}")
    
    print("\n❌ Problems:")
    print("   - No follow-ups on interesting topics")
    print("   - Doesn't dig deeper into weaknesses (AWS)")
    print("   - Doesn't explore strengths (Docker)")
    print("   - Generic questions, not contextual")


# Run the examples
if __name__ == "__main__":
    asyncio.run(example_stateful_interview())
    asyncio.run(comparison_without_memory())