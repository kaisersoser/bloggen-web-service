import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth"
import { serverLogger } from '@/lib/logger/server'

export async function POST() {
  try {
    // Get the session to ensure user is authenticated
    const session = await getServerSession(authOptions);

    if (!session?.user?.email) {
      return Response.json({ error: 'Unauthorized' }, { status: 401 });
    }

  // Generate a unique task ID using timestamp and random component
  const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;

  serverLogger.info('Generated blog generation task ID', { userEmail: session.user.email, taskId });

    return Response.json({ 
      task_id: taskId,
      user_email: session.user.email 
    });
  } catch (error) {
    serverLogger.error('Error generating task ID', error);
    return Response.json({ error: 'Failed to generate task ID' }, { status: 500 });
  }
}