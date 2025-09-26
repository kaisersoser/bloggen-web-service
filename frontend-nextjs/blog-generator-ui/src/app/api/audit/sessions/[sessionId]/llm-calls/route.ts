import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { serverLogger } from '@/lib/logger/server';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;
    const data = await request.json();

    const {
      model,
      input_tokens,
      output_tokens,
      input_cost,
      output_cost,
      total_cost,
      phase,
      agent_role,
      call_type
    } = data;

    // Verify the audit session exists
    const auditSession = await prisma.auditSession.findUnique({
      where: { id: sessionId }
    });

    if (!auditSession) {
      return NextResponse.json(
        { error: 'Audit session not found' },
        { status: 404 }
      );
    }

    // Create the LLM call record
    const llmCall = await prisma.lLMCall.create({
      data: {
        id: crypto.randomUUID(),
        auditSessionId: sessionId,
        model: model || 'unknown',
        inputTokens: parseInt(input_tokens) || 0,
        outputTokens: parseInt(output_tokens) || 0,
        inputCost: parseFloat(input_cost) || 0,
        outputCost: parseFloat(output_cost) || 0,
        totalCost: parseFloat(total_cost) || 0,
        phase: phase || 'unknown',
        agentRole: agent_role || 'unknown',
        callType: call_type || 'actual',
        timestamp: new Date()
      }
    });

    // Update the audit session's total cost
    await prisma.auditSession.update({
      where: { id: sessionId },
      data: {
        totalCost: {
          increment: parseFloat(total_cost) || 0
        }
      }
    });

    return NextResponse.json(llmCall, { status: 201 });

  } catch (error) {
    serverLogger.error('Error creating LLM call', error);
    return NextResponse.json(
      { error: 'Failed to create LLM call' },
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

    // Get all LLM calls for this session
    const llmCalls = await prisma.lLMCall.findMany({
      where: { auditSessionId: sessionId },
      orderBy: { timestamp: 'asc' }
    });

    return NextResponse.json(llmCalls);

  } catch (error) {
    serverLogger.error('Error getting LLM calls', error);
    return NextResponse.json(
      { error: 'Failed to get LLM calls' },
      { status: 500 }
    );
  }
}
