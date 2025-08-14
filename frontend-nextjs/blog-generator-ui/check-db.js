const { PrismaClient } = require('@prisma/client');

async function checkDatabase() {
  const prisma = new PrismaClient();
  
  try {
    console.log('🔍 Checking database structure...\n');
    
    // Check if tables exist by trying to query them
    console.log('📊 Checking User table...');
    const userCount = await prisma.user.count();
    console.log(`✅ User table exists - ${userCount} users found`);
    
    console.log('\n📊 Checking Blog table...');
    const blogCount = await prisma.blog.count();
    console.log(`✅ Blog table exists - ${blogCount} blogs found`);
    
    console.log('\n📊 Checking AuditSession table...');
    const auditCount = await prisma.auditSession.count();
    console.log(`✅ AuditSession table exists - ${auditCount} audit sessions found`);
    
    // Check specific columns exist in Blog table
    console.log('\n🔍 Checking Blog table structure...');
    const sampleBlog = await prisma.blog.findFirst({
      select: {
        id: true,
        userId: true,
        topic: true,
        instructions: true,
        content: true,
        heroImageUrl: true,
        status: true,
        progress: true,
        currentStep: true,
        error: true,
        createdAt: true,
        updatedAt: true,
        completedAt: true
      }
    });
    
    if (sampleBlog) {
      console.log('✅ All Blog columns accessible:', Object.keys(sampleBlog));
    } else {
      console.log('ℹ️  No blogs exist, but structure query succeeded');
    }
    
    // Test creating a sample user (if none exists)
    if (userCount === 0) {
      console.log('\n🔧 Creating test user...');
      const testUser = await prisma.user.create({
        data: {
          email: 'test@example.com',
          name: 'Test User',
          role: 'FREE'
        }
      });
      console.log('✅ Test user created:', testUser.id);
    }
    
    // Test creating a sample blog
    console.log('\n🔧 Testing blog creation...');
    const firstUser = await prisma.user.findFirst();
    if (firstUser) {
      const testBlog = await prisma.blog.create({
        data: {
          userId: firstUser.id,
          topic: 'Test Blog Topic',
          instructions: 'Test instructions',
          status: 'QUEUED',
          progress: 0,
          currentStep: 'Testing...'
        }
      });
      console.log('✅ Test blog created successfully:', testBlog.id);
      
      // Clean up test blog
      await prisma.blog.delete({ where: { id: testBlog.id } });
      console.log('🧹 Test blog cleaned up');
    }
    
    console.log('\n🎉 Database structure verification complete!');
    
  } catch (error) {
    console.error('❌ Database check failed:', error.message);
    console.error('Full error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

checkDatabase();
