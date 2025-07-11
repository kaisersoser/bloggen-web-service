"""
CrewAI Blog Generation Flow - Structured workflow with real-time status updates

This module implements a Flow-based approach to blog generation using CrewAI Flows.
Instead of relying on log interception, it provides explicit control points where
we can send meaningful, business-relevant status updates to the frontend.

The flow is structured into clear phases:
1. Research Phase - Gather information and insights on the topic
2. Content Generation - Create the initial blog draft with images
3. Fact Checking - Verify accuracy and add credibility
4. Finalization - Polish and format the final blog post

Each phase sends custom status updates via WebSocket to provide real-time feedback.
The content generation phase now includes automatic image integration via Unsplash API.
"""

from crewai.flow.flow import Flow, listen, start
from crewai import Agent, Task, Crew
from datetime import datetime
import time
import os


class BlogGenerationFlow(Flow):
    """
    Structured blog generation workflow with real-time status updates.
    
    This Flow orchestrates the blog generation process through distinct phases,
    sending meaningful status updates to the frontend at each stage.
    """
    
    def __init__(self, socketio=None, task_id=None, room_id=None):
        """
        Initialize the blog generation flow.
        
        Args:
            socketio: Flask-SocketIO instance for real-time communication
            task_id (str): Unique task identifier for tracking
            room_id (str): WebSocket room for broadcasting updates
        """
        super().__init__()
        self.socketio = socketio
        self.task_id = task_id
        self.room_id = room_id
        self.topic = None
        self.current_year = None
        
        # Progress tracking
        self.total_steps = 4
        self.current_step = 0
        
        # Results storage
        self.research_results = None
        self.initial_content = None
        self.fact_checked_content = None
        self.final_blog_post = None

    def _send_status_update(self, message, step, detail=None):
        """
        Send a status update to the frontend via WebSocket.
        
        Args:
            message (str): Human-readable status message
            step (int): Current progress step (1-4)
            detail (str, optional): Additional detail information
        """
        if self.socketio and self.task_id and self.room_id:
            update_data = {
                'task_id': self.task_id,
                'status': 'in_progress',
                'message': message,
                'step': step,
                'total_steps': self.total_steps
            }
            
            if detail:
                update_data['detail'] = detail
                
            self.socketio.emit('status_update', update_data, to=self.room_id)
            
            # Also send log update to track the sequence of actions
            self._send_log_update(f"Step {step}/{self.total_steps}: {message}")
            
            # Small delay to ensure message delivery
            time.sleep(0.1)

    def _send_log_update(self, log_message):
        """
        Send a log update to track the sequence of Flow actions.
        
        Args:
            log_message (str): Log message to send to frontend
        """
        if self.socketio and self.task_id and self.room_id:
            from datetime import datetime
            self.socketio.emit('log_update', {
                'task_id': self.task_id,
                'log': log_message,
                'timestamp': datetime.now().isoformat()
            }, to=self.room_id)

    @start()
    def initialize_flow(self):
        """
        Initialize the flow with input parameters and start the research phase.
        
        The inputs are available through the Flow's state after kickoff() is called.
        
        Returns:
            dict: Flow initialization data
        """
        # Access inputs from the Flow's state (set by kickoff method)
        flow_state = self.state if hasattr(self, 'state') else {}
        
        # Extract inputs from the flow state
        topic = flow_state.get('topic') if isinstance(flow_state, dict) else None
        current_year = flow_state.get('current_year') if isinstance(flow_state, dict) else None
        
        # Store for later use
        self.topic = topic
        self.current_year = current_year
        
        # Send initial log
        self._send_log_update(f"🚀 Flow initialized for topic: '{topic}'")
        
        self._send_status_update(
            f"Starting research on '{topic}'...", 
            1, 
            "Initializing research agents and gathering initial insights"
        )
        
        return {
            "topic": topic,
            "current_year": current_year,
            "status": "initialized"
        }

    @listen(initialize_flow)
    def research_phase(self, initialization_data):
        """
        Phase 1: Research and gather information on the topic.
        
        This phase uses the Senior Researcher agent to gather comprehensive
        information about the topic, including recent trends, statistics, and insights.
        
        Args:
            initialization_data (dict): Data from initialization
            
        Returns:
            dict: Research results and insights
        """
        self._send_status_update(
            "Conducting deep research on the topic...", 
            1, 
            "Senior Researcher is analyzing trends, gathering data, and finding key insights"
        )
        
        self._send_log_update("🔍 Creating Senior Researcher agent...")
        
        # Create Research Agent
        researcher = Agent(
            role='Senior Researcher',
            goal='Uncover cutting-edge developments and insights in the given topic',
            verbose=True,
            backstory="""You work at a leading tech think tank.
            Your expertise lies in identifying emerging trends and providing 
            comprehensive analysis on complex topics. You have a knack for 
            finding the most relevant and up-to-date information.""",
            tools=self._get_research_tools(),
            allow_delegation=False
        )
        
        # Create Research Task
        research_task = Task(
            description=f"""Conduct a comprehensive research analysis on "{self.topic}".
            Your final answer MUST include:
            1. Current state and recent developments (as of {self.current_year})
            2. Key statistics and data points
            3. Main challenges and opportunities
            4. Expert opinions and market insights
            5. Future trends and predictions
            
            Focus on finding the most relevant and interesting information that would 
            make for an engaging blog post.""",
            expected_output="""A comprehensive research report with:
            - 5 key insights about the topic
            - Recent statistics and data
            - Current trends and developments
            - Expert quotes or opinions
            - Future outlook and predictions""",
            agent=researcher
        )
        
        # Execute research
        self._send_status_update(
            "Gathering latest insights and trends...", 
            1, 
            "Analyzing market data, expert opinions, and recent developments"
        )
        
        self._send_log_update("📊 Executing research crew to gather insights...")
        
        crew = Crew(
            agents=[researcher],
            tasks=[research_task],
            verbose=True
        )
        
        research_results = crew.kickoff()
        self.research_results = research_results
        
        self._send_log_update("✅ Research phase completed successfully")
        
        self._send_status_update(
            "Research completed - found valuable insights!", 
            1, 
            "Moving to content generation phase"
        )
        
        return {
            "research_results": str(research_results),
            "topic": self.topic,
            "current_year": self.current_year
        }

    @listen(research_phase)
    def content_generation_phase(self, research_data):
        """
        Phase 2: Generate engaging blog content based on research.
        
        Uses the research findings to create a well-structured, engaging blog post
        that incorporates the insights and data discovered in the research phase.
        
        Args:
            research_data (dict): Results from the research phase
            
        Returns:
            dict: Generated blog content
        """
        self._send_status_update(
            "Creating engaging blog content...", 
            2, 
            "Content Writer is crafting a compelling narrative based on research findings"
        )
        
        self._send_log_update("✍️ Creating Content Writer agent...")
        
        # Create Content Writer Agent with image search capabilities
        writer = Agent(
            role='Tech Content Strategist & Visual Designer',
            goal='Create compelling blog posts with professional images using available tools',
            verbose=True,
            backstory="""You are a tech content strategist who ALWAYS enhances articles with professional images. 
            You have access to an unsplash_image_search tool that finds perfect images for any topic.
            
            CRITICAL: You MUST use the unsplash_image_search tool to add at least 2 images to every blog post.
            Never write a blog post without calling this tool multiple times to get relevant images.
            
            Your process:
            1. Write introduction
            2. Call unsplash_image_search tool for hero image  
            3. Write main content sections
            4. Call unsplash_image_search tool for supporting images
            5. Complete the article with conclusion
            
            You always insert the exact Markdown returned by the tool without modification.""",
            tools=self._get_content_tools(),  # Include Unsplash and research tools
            allow_delegation=False
        )
        
        # Create Content Generation Task with image integration
        content_task = Task(
            description=f"""You are creating an engaging blog post about "{self.topic}" with professional images.

            Research findings to incorporate:
            {research_data['research_results']}
            
            STEP-BY-STEP INSTRUCTIONS:
            
            1. Write a compelling headline and introduction paragraph
            
            2. **MANDATORY**: Use the unsplash_image_search tool to find a hero image:
               - Call: unsplash_image_search(query="{self.topic}", count=1, orientation="landscape")
               - Insert the returned Markdown immediately after your introduction
            
            3. Write the main content with 3-4 sections covering key insights
            
            4. **MANDATORY**: Use the unsplash_image_search tool again for a supporting image:
               - Call: unsplash_image_search(query="{self.topic} technology business", count=1, orientation="landscape")
               - Insert the returned Markdown in the middle of your content
            
            5. Write your conclusion with actionable insights
            
            6. **OPTIONAL**: Add one more image if it enhances the content:
               - Call: unsplash_image_search(query="innovation technology future", count=1, orientation="landscape")
            
            REQUIREMENTS:
            - 800-1200 words total
            - Professional, engaging tone
            - Include research insights and data
            - **YOU MUST CALL THE UNSPLASH_IMAGE_SEARCH TOOL AT LEAST 2 TIMES**
            - Insert the exact Markdown returned by the tool (don't modify it)
            
            The unsplash_image_search tool will return properly formatted Markdown like:
            ![Alt text](image-url)
            *Photo credit*
            
            Just copy and paste this output directly into your blog post.""",
            expected_output="""A complete blog post with:
            - Compelling headline
            - Engaging introduction
            - **AT LEAST 2 IMAGES** inserted using the unsplash_image_search tool
            - Well-structured body with 3-4 main sections
            - Integration of research findings and data
            - Professional images with proper Markdown formatting and attribution
            - Images strategically placed to enhance content flow and engagement
            - Strong conclusion with key takeaways
            - Professional yet accessible tone
            - 800-1200 words total
            
            CRITICAL: The output MUST contain actual images retrieved using the unsplash_image_search tool, 
            not placeholder text or image descriptions.""",
            agent=writer
        )
        
        # Execute content generation with image integration
        self._send_status_update(
            "Writing compelling content and selecting images...", 
            2, 
            "Crafting narrative and integrating professional images from Unsplash"
        )
        
        self._send_log_update("📝🖼️ Executing content generation with image integration...")
        
        crew = Crew(
            agents=[writer],
            tasks=[content_task],
            verbose=True
        )
        
        content_results = crew.kickoff()
        self.initial_content = content_results
        
        self._send_log_update("✅ Content generation with images completed successfully")
        
        self._send_status_update(
            "Content with professional images completed!", 
            2, 
            "Proceeding to fact-checking and verification"
        )
        
        return {
            "content": str(content_results),
            "research_data": research_data
        }

    @listen(content_generation_phase)
    def fact_checking_phase(self, content_data):
        """
        Phase 3: Fact-check and verify the content accuracy.
        
        Reviews the generated content for accuracy, credibility, and ensures
        all claims are well-supported and factually correct.
        
        Args:
            content_data (dict): Generated content from previous phase
            
        Returns:
            dict: Fact-checked and verified content
        """
        self._send_status_update(
            "Fact-checking and verifying information...", 
            3, 
            "Quality Assurance Editor is verifying claims and ensuring accuracy"
        )
        
        self._send_log_update("🔍 Creating Quality Assurance Editor agent...")
        
        # Create Fact Checker Agent
        fact_checker = Agent(
            role='Quality Assurance Editor',
            goal='Ensure all content is accurate, credible, and well-sourced',
            verbose=True,
            backstory="""You are a meticulous editor with a keen eye for detail. 
            Your expertise lies in fact-checking, ensuring accuracy, and maintaining 
            high editorial standards. You have a reputation for catching errors 
            and improving content quality.""",
            tools=self._get_research_tools(),  # Same tools for verification
            allow_delegation=False
        )
        
        # Create Fact Checking Task
        fact_check_task = Task(
            description=f"""Review and fact-check the following blog post about "{self.topic}":
            
            {content_data['content']}
            
            Your responsibilities:
            1. Verify factual accuracy of all claims and statistics
            2. Check for logical consistency and flow
            3. Ensure all data points are current and relevant
            4. Suggest improvements for clarity and credibility
            5. Add source references where beneficial
            6. Maintain the engaging tone while ensuring accuracy
            
            Return the improved, fact-checked version of the blog post.""",
            expected_output="""A fact-checked and improved blog post with:
            - Verified facts and statistics
            - Improved clarity and flow
            - Enhanced credibility
            - Maintained engaging tone
            - Any necessary corrections or improvements""",
            agent=fact_checker
        )
        
        # Execute fact checking
        self._send_status_update(
            "Verifying claims and cross-referencing sources...", 
            3, 
            "Ensuring all information is accurate and up-to-date"
        )
        
        self._send_log_update("🔍 Executing fact-checking crew...")
        
        crew = Crew(
            agents=[fact_checker],
            tasks=[fact_check_task],
            verbose=True
        )
        
        fact_checked_results = crew.kickoff()
        self.fact_checked_content = fact_checked_results
        
        self._send_log_update("✅ Fact-checking phase completed successfully")
        
        self._send_status_update(
            "Fact-checking completed - content verified!", 
            3, 
            "Moving to final polishing and formatting"
        )
        
        return {
            "fact_checked_content": str(fact_checked_results),
            "original_content": content_data
        }

    @listen(fact_checking_phase)
    def finalization_phase(self, verified_content_data):
        """
        Phase 4: Finalize and polish the blog post.
        
        Applies final formatting, polish, and ensures the blog post is ready
        for publication with optimal readability and engagement.
        
        Args:
            verified_content_data (dict): Fact-checked content
            
        Returns:
            str: Final polished blog post
        """
        self._send_status_update(
            "Finalizing and polishing your blog post...", 
            4, 
            "Chief Editor is applying final touches and formatting"
        )
        
        self._send_log_update("✨ Creating Chief Editor agent...")
        
        # Create Editor Agent
        editor = Agent(
            role='Chief Editor',
            goal='Transform content into polished, publication-ready blog posts',
            verbose=True,
            backstory="""You are an experienced Chief Editor with a track record 
            of producing viral, engaging content. Your expertise lies in final 
            polish, formatting, and ensuring content is optimized for readability 
            and engagement.""",
            tools=[],
            allow_delegation=False
        )
        
        # Create Finalization Task
        finalization_task = Task(
            description=f"""Polish and finalize the following blog post about "{self.topic}":
            
            {verified_content_data['fact_checked_content']}
            
            Your final polish should include:
            1. Perfect formatting and structure
            2. Engaging subheadings and section breaks
            3. Optimized readability and flow
            4. Strong call-to-action or conclusion
            5. SEO-friendly elements (without compromising quality)
            6. Final grammar and style review
            
            Deliver a publication-ready blog post that will engage and inform readers.""",
            expected_output="""A polished, publication-ready blog post with:
            - Perfect formatting and structure
            - Engaging headings and subheadings
            - Optimized readability
            - Strong conclusion
            - Professional presentation
            - Ready for immediate publication""",
            agent=editor
        )
        
        # Execute finalization
        self._send_status_update(
            "Applying final formatting and polish...", 
            4, 
            "Optimizing readability and adding finishing touches"
        )
        
        self._send_log_update("✨ Executing finalization crew...")
        
        crew = Crew(
            agents=[editor],
            tasks=[finalization_task],
            verbose=True
        )
        
        final_results = crew.kickoff()
        self.final_blog_post = final_results
        
        self._send_log_update("🎉 Blog generation completed successfully!")
        
        self._send_status_update(
            "Blog post completed and ready!", 
            4, 
            "Your professional blog post has been generated successfully"
        )
        
        return str(final_results)

    def _get_research_tools(self):
        """
        Get the research tools for agents that need them.
        
        Returns:
            list: List of research tools (SerperDevTool, ScrapeWebsiteTool)
        """
        try:
            from crewai_tools import SerperDevTool, ScrapeWebsiteTool
            return [SerperDevTool(), ScrapeWebsiteTool()]
        except ImportError:
            # Fallback if tools are not available
            return []

    def _get_content_tools(self):
        """
        Get the content creation tools including Unsplash image integration.
        
        Returns:
            list: List of content creation tools (UnsplashImageTool)
        """
        tools = []
        
        # Add Unsplash tool if available
        try:
            from .tools import create_unsplash_tool
            unsplash_tool = create_unsplash_tool()
            tools.append(unsplash_tool)
            self._send_log_update(f"✅ Unsplash tool added successfully (Tool: {unsplash_tool.name})")
        except ImportError as e:
            # Fallback if Unsplash tool is not available
            self._send_log_update(f"❌ Unsplash tool import failed: {str(e)}")
        except Exception as e:
            self._send_log_update(f"❌ Unsplash tool creation failed: {str(e)}")
        
        # Add research tools for content enhancement
        research_tools = self._get_research_tools()
        tools.extend(research_tools)
        
        self._send_log_update(f"🔧 Total tools available to agent: {len(tools)} ({[t.name for t in tools]})")
        
        return tools
