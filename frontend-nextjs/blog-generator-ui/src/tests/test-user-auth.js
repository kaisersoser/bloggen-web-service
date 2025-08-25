const { PrismaClient } = require('@prisma/client');

async function testUserAuth() {
  const prisma = new PrismaClient();
  
  try {
    console.log('🔍 Testing user authentication and permissions...\n');
    
    // Find an existing user
    const existingUser = await prisma.user.findFirst();
    console.log('👤 Found user:', {
      id: existingUser?.id,
      email: existingUser?.email,
      role: existingUser?.role
    });
    
    if (existingUser) {
      console.log('\n🔧 Testing blog creation for existing user...');
      
      // Test the exact same operation that happens in the API route
      const newBlog = await prisma.blog.create({
        data: {
          userId: existingUser.id,
          topic: 'RLS Test Blog',
          instructions: 'Testing RLS permissions',
          status: 'QUEUED',
          progress: 0,
          currentStep: 'Starting...'
        }
      });
      
      console.log('✅ Blog created successfully:', {
        id: newBlog.id,
        userId: newBlog.userId,
        topic: newBlog.topic,
        status: newBlog.status
      });
      
      // Test reading the blog back
      const retrievedBlog = await prisma.blog.findUnique({
        where: { id: newBlog.id }
      });
      
      console.log('✅ Blog retrieved successfully:', !!retrievedBlog);
      
      // Clean up
      await prisma.blog.delete({ where: { id: newBlog.id } });
      console.log('🧹 Test blog cleaned up');
    }
    
    // Test user generation limit check
    console.log('\n🔍 Testing user generation limit logic...');
    const userStats = await prisma.user.findUnique({
      where: { id: existingUser?.id },
      select: {
        monthlyGenerations: true,
        role: true,
        lastGenerationReset: true
      }
    });
    
    console.log('📊 User stats:', userStats);
    
    console.log('\n🎉 User authentication tests complete!');
    
  } catch (error) {
    console.error('❌ User auth test failed:', error.message);
    console.error('Error code:', error.code);
    console.error('Full error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

testUserAuth();
