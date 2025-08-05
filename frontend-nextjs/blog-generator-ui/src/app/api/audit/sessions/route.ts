import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { sessionType, userId, blogId, startTime } = body;

    // Validate required fields
    if (!sessionType || !userId) {
      return NextResponse.json(
        { error: 'sessionType and userId are required' },
        { status: 400 }
      );
    }

    // Create audit session
    const auditSession = await prisma.auditSession.create({
      data: {
        sessionType,
        userId,
        blogId: blogId || null,
        startTime: startTime ? new Date(startTime) : new Date(),
        totalCost: 0,
        totalTokens: 0,
        inputTokens: 0,
        outputTokens: 0,
        callCount: 0
      }
    });

    return NextResponse.json(auditSession, { status: 201 });

  } catch (error) {
    console.error('Error creating audit session:', error);
    return NextResponse.json(
      { error: 'Failed to create audit session' },
      { status: 500 }
    );
  }
}
