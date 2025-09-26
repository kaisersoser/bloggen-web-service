import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { serverLogger } from '@/lib/logger/server';

// Type for audit session data structure
interface AuditSessionData {
  id: string;
  createdAt: Date;
  totalCost: number;
  totalTokens: number;
  callCount: number;
  user: {
    name: string | null;
    email: string | null;
    role: string;
  } | null;
  blog: {
    topic: string;
    status: string;
  } | null;
  llmCalls: {
    phase: string;
    model: string;
    totalCost: number;
  }[];
}

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session || !session.user) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    // Check if user is admin
    const user = await prisma.user.findUnique({
      where: { id: session.user.id }
    });

    if (!user || user.role !== 'ADMIN') {
      return NextResponse.json({ error: "Admin access required" }, { status: 403 });
    }

    // Get query parameters
    const { searchParams } = new URL(req.url);
    const days = parseInt(searchParams.get('days') || '30');

    // Calculate date range
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - days);

    // Get audit sessions with aggregated data
    const auditSessions: AuditSessionData[] = await prisma.auditSession.findMany({
      where: {
        createdAt: {
          gte: fromDate
        }
      },
      include: {
        llmCalls: true,
        user: {
          select: {
            name: true,
            email: true,
            role: true
          }
        },
        blog: {
          select: {
            topic: true,
            status: true
          }
        }
      },
      orderBy: {
        createdAt: 'desc'
      }
    });

  // Process data for analytics
  const dailyLLMCosts: { [key: string]: number } = {};
  const dailySerperCosts: { [key: string]: number } = {};
    const phaseCosts: { [key: string]: number } = {};
    const modelCosts: { [key: string]: number } = {};
    const userRoleCosts: { [key: string]: number } = {};
    
    let totalCost = 0;
    let totalTokens = 0;
    let totalCalls = 0;

    auditSessions.forEach((session: AuditSessionData) => {
      const dateKey = session.createdAt.toISOString().split('T')[0];
      
      // Per-call accumulation for daily LLM vs Serper API costs
      session.llmCalls.forEach((call: { phase: string; model: string; totalCost: number }) => {
        const isSerper = call.model === 'serper_api';
        if (isSerper) {
          if (!dailySerperCosts[dateKey]) dailySerperCosts[dateKey] = 0;
          dailySerperCosts[dateKey] += call.totalCost;
        } else {
          if (!dailyLLMCosts[dateKey]) dailyLLMCosts[dateKey] = 0;
          dailyLLMCosts[dateKey] += call.totalCost;
        }
      });
      
      // Session totals
      totalCost += session.totalCost;
      totalTokens += session.totalTokens;
      totalCalls += session.callCount;

      // Phase and model breakdown
      session.llmCalls.forEach((call: { phase: string; model: string; totalCost: number }) => {
        // Phase costs
        if (!phaseCosts[call.phase]) {
          phaseCosts[call.phase] = 0;
        }
        phaseCosts[call.phase] += call.totalCost;

        // Model costs
        if (!modelCosts[call.model]) {
          modelCosts[call.model] = 0;
        }
        modelCosts[call.model] += call.totalCost;
      });

      // User role costs
      const userRole = session.user?.role || 'unknown';
      if (!userRoleCosts[userRole]) {
        userRoleCosts[userRole] = 0;
      }
      userRoleCosts[userRole] += session.totalCost;
    });

    // Format daily costs for charting (fill missing dates with 0)
    const chartData: Array<{ date: string; totalCost: number; llmCost: number; serperCost: number }> = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateKey = date.toISOString().split('T')[0];
      const llmCost = dailyLLMCosts[dateKey] || 0;
      const serperCost = dailySerperCosts[dateKey] || 0;
      chartData.push({
        date: dateKey,
        totalCost: llmCost + serperCost,
        llmCost,
        serperCost
      });
    }

    // Aggregate totals by model for llm vs serper
    let serperCostTotal = 0;
    let llmCostTotal = 0;
    Object.entries(modelCosts).forEach(([model, cost]) => {
      if (model === 'serper_api') serperCostTotal += cost;
      else llmCostTotal += cost;
    });

    return NextResponse.json({
      summary: {
        totalCost,
        totalTokens,
        totalCalls,
        totalSessions: auditSessions.length,
        serperCost: serperCostTotal,
        llmCost: llmCostTotal,
        dateRange: {
          from: fromDate.toISOString(),
          to: new Date().toISOString()
        }
      },
      chartData,
      breakdowns: {
        byPhase: Object.entries(phaseCosts).map(([phase, cost]) => ({
          phase,
          cost
        })),
        byModel: Object.entries(modelCosts).map(([model, cost]) => ({
          model,
          cost
        })),
        byUserRole: Object.entries(userRoleCosts).map(([role, cost]) => ({
          role,
          cost
        }))
      }
    });

  } catch (error) {
    serverLogger.error('Error fetching audit analytics', { error });
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
