import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '10');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    // Get audit sessions for this user
    const auditSessions = await prisma.auditSession.findMany({
      where: { userId },
      include: {
        llmCalls: true,
        blog: {
          select: { id: true, topic: true, status: true }
        }
      },
      orderBy: { createdAt: 'desc' },
      take: limit,
      skip: offset
    });

    // Calculate aggregated stats
    const totalSessions = await prisma.auditSession.count({
      where: { userId }
    });

    const aggregateStats = await prisma.auditSession.aggregate({
      where: { userId },
      _sum: {
        totalCost: true,
        totalTokens: true,
        inputTokens: true,
        outputTokens: true,
        callCount: true
      }
    });

    // Calculate monthly stats (current month)
    const currentMonth = new Date();
    currentMonth.setDate(1);
    currentMonth.setHours(0, 0, 0, 0);

    const monthlyStats = await prisma.auditSession.aggregate({
      where: {
        userId,
        createdAt: {
          gte: currentMonth
        }
      },
      _sum: {
        totalCost: true,
        totalTokens: true,
        callCount: true
      }
    });

    const response = {
      sessions: auditSessions.map(session => ({
        ...session,
        duration_seconds: session.endTime && session.startTime
          ? (session.endTime.getTime() - session.startTime.getTime()) / 1000
          : null,
        start_time: session.startTime.toISOString(),
        end_time: session.endTime?.toISOString() || null
      })),
      pagination: {
        total: totalSessions,
        limit,
        offset,
        hasMore: (offset + limit) < totalSessions
      },
      totalStats: {
        totalCost: aggregateStats._sum.totalCost || 0,
        totalTokens: aggregateStats._sum.totalTokens || 0,
        inputTokens: aggregateStats._sum.inputTokens || 0,
        outputTokens: aggregateStats._sum.outputTokens || 0,
        totalCalls: aggregateStats._sum.callCount || 0,
        totalSessions
      },
      monthlyStats: {
        totalCost: monthlyStats._sum.totalCost || 0,
        totalTokens: monthlyStats._sum.totalTokens || 0,
        totalCalls: monthlyStats._sum.callCount || 0
      }
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Error getting user audit summary:', error);
    return NextResponse.json(
      { error: 'Failed to get user audit summary' },
      { status: 500 }
    );
  }
}
