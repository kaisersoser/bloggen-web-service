const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient({
  log: ['query', 'info', 'warn', 'error'],
});

async function updateUserToAdmin() {
  try {
    console.log('🔍 Searching for Charles Vogt...');
    
    // First, find the user
    const users = await prisma.user.findMany({
      where: {
        OR: [
          { name: { contains: 'Charles', mode: 'insensitive' } },
          { name: { contains: 'Vogt', mode: 'insensitive' } },
          { email: { contains: 'vogt', mode: 'insensitive' } },
          { email: { contains: 'charles', mode: 'insensitive' } }
        ]
      }
    });

    console.log(`Found ${users.length} matching users:`);
    users.forEach(user => {
      console.log(`- ID: ${user.id}, Name: ${user.name}, Email: ${user.email}, Role: ${user.role}`);
    });

    if (users.length === 0) {
      console.log('⚠️  No users found matching Charles Vogt. Showing all users:');
      const allUsers = await prisma.user.findMany();
      allUsers.forEach(user => {
        console.log(`- ID: ${user.id}, Name: ${user.name}, Email: ${user.email}, Role: ${user.role}`);
      });
      return;
    }

    // Update the first matching user to ADMIN role
    const userToUpdate = users[0];
    console.log(`\n🔄 Updating user ${userToUpdate.name} (${userToUpdate.email}) to ADMIN role...`);

    const updatedUser = await prisma.user.update({
      where: { id: userToUpdate.id },
      data: { role: 'ADMIN' }
    });

    console.log('✅ User updated successfully!');
    console.log(`Updated user: ${updatedUser.name} (${updatedUser.email}) - Role: ${updatedUser.role}`);

  } catch (error) {
    console.error('❌ Error updating user:', error.message);
    console.error('Full error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

console.log('🚀 Starting user role update...');
updateUserToAdmin();
