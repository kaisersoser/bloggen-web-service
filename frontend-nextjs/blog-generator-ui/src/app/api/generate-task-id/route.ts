import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"

export async function POST() {
  try {
    // Get the session to ensure user is authenticated
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return Response.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Generate a unique task ID using timestamp and random component
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;

    console.log('Generated task ID for user:', session.user.email, 'Task ID:', taskId);

    return Response.json({ 
      task_id: taskId,
      user_email: session.user.email 
    });
  } catch (error) {
    console.error('Error generating task ID:', error);
    return Response.json({ error: 'Failed to generate task ID' }, { status: 500 });
  }
}