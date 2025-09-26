import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { serverLogger } from '@/lib/logger/server';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const body = await request.json();
    const { endTime } = body;
    const { sessionId } = await params;

    // Update audit session (remove status field since it doesn't exist in schema)
    const updatedSession = await prisma.auditSession.update({
      where: { id: sessionId },
      data: {
        endTime: endTime ? new Date(endTime) : new Date()
      }
    });

    return NextResponse.json(updatedSession);

  } catch (error) {
    serverLogger.error('Error completing audit session', error);
    return NextResponse.json(
      { error: 'Failed to complete audit session' },
      { status: 500 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;

    const auditSession = await prisma.auditSession.findUnique({
      where: { id: sessionId },
      include: {
        llmCalls: true,
        user: {
          select: { id: true, name: true, email: true }
        },
        blog: {
          select: { id: true, topic: true, status: true }
        }
      }
    });

    if (!auditSession) {
      return NextResponse.json(
        { error: 'Audit session not found' },
        { status: 404 }
      );
    }

    // Calculate duration
    const duration = auditSession.endTime && auditSession.startTime
      ? (auditSession.endTime.getTime() - auditSession.startTime.getTime()) / 1000
      : null;

    const response = {
      ...auditSession,
      duration_seconds: duration,
      start_time: auditSession.startTime.toISOString(),
      end_time: auditSession.endTime?.toISOString() || null
    };

    return NextResponse.json(response);

  } catch (error) {
    serverLogger.error('Error getting audit session', error);
    return NextResponse.json(
      { error: 'Failed to get audit session' },
      { status: 500 }
    );
  }
}
