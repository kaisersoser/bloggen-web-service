"use client"
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-6xl font-bold text-gray-900 mb-6">
            AI Blog Generator
          </h1>
          <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
            Create engaging, well-researched blog posts with the power of AI. 
            Our CrewAI-powered system researches, writes, and fact-checks your content automatically.
          </p>
          
          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">🔍 Research</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  AI agents research your topic using the latest information from the web
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">✍️ Generate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  Content creators write engaging, well-structured articles
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">✅ Verify</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  Fact-checkers ensure accuracy and quality before finalization
                </p>
              </CardContent>
            </Card>
          </div>
          
          <Link href="/blog">
            <Button size="lg" className="text-lg px-8 py-4">
              Start Generating →
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
