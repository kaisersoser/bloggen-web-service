"use client"
import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import ReactMarkdown from "react-markdown";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function BlogGenerator() {
  const [topic, setTopic] = useState("");
  const [instructions, setInstructions] = useState("");
  const [requestId, setRequestId] = useState(null);
  const [blogContent, setBlogContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const handleGenerateBlog = async () => {
    setLoading(true);
    setBlogContent("");
    try {
      const response = await fetch("http://localhost:5000/generate-blog", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ topic }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate blog");
      }

      const data = await response.json();
      setBlogContent(data.blogContent); // <-- Set content directly
      setShowModal(true); // Optionally open modal automatically
    } catch (error) {
      console.error("Error generating blog:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-4">
      <Card>
        <CardContent className="space-y-4">
          <h1 className="text-xl font-bold">Blog Generator</h1>
          <Input
            placeholder="Enter blog topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
          <Textarea
            placeholder="Enter writing instructions (tone, format, etc.)"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
          <Button onClick={handleGenerateBlog} disabled={loading}>
            {loading ? "Submitting..." : "Generate Blog"}
          </Button>
        </CardContent>
      </Card>

      {blogContent && (
        <Card>
          <CardContent className="space-y-2">
            <h2 className="text-lg font-semibold">Blog Ready</h2>
            <Button onClick={() => setShowModal(true)}>View</Button>
          </CardContent>
        </Card>
      )}

      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-h-screen overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Generated Blog</DialogTitle>
          </DialogHeader>
          <div className="prose">
            <ReactMarkdown>{blogContent}</ReactMarkdown>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
