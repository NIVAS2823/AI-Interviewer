import asyncio
from app.utils.videosdk_agent import VideoSDKAgentService

async def main():
    vs = VideoSDKAgentService()

    print("\n=== 1) Creating Meeting ===")
    meeting_id = await vs.create_meeting()
    print("MEETING ID:", meeting_id)

    print("\n=== 2) Creating Meeting Token ===")
    token = await vs.get_meeting_token(meeting_id)
    print("MEETING TOKEN:", token)

    print("\n=== 3) Creating AI Agent ===")
    agent_id = await vs.create_ai_agent(
        meeting_id=meeting_id,
        interviewer_name="Sarah",
        questions=[
            "Can you introduce yourself?",
            "Tell me about a recent project you worked on."
        ],
        system_prompt="You are Sarah, a friendly professional AI interviewer."
    )
    print("AGENT ID:", agent_id)

    print("\n=== 4) Starting Agent ===")
    started = await vs.start_agent(meeting_id, agent_id)
    print("AGENT STARTED:", started)

    print("\n=== 5) Stopping Agent ===")
    stopped = await vs.stop_agent(agent_id)
    print("AGENT STOPPED:", stopped)

    print("\n=== 6) Ending Meeting ===")
    ended = await vs.end_meeting(meeting_id)
    print("MEETING ENDED:", ended)

asyncio.run(main())
