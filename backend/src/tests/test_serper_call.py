import os, asyncio, asyncpg, time
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from bloggen.tools_manager import ToolsManager

async def main():
    # Ensure DB and key
    db = os.getenv('DATABASE_URL')
    key = os.getenv('SERPER_API_KEY')
    if not db:
        print('Missing DATABASE_URL')
        return
    if not key:
        print('Missing SERPER_API_KEY')
        return
    # Fetch an existing ADMIN user (fallback to any user) to satisfy FK
    admin_user_id = None
    try:
        conn = await asyncpg.connect(db)
        admin_user_id = await conn.fetchval("SELECT id FROM users WHERE role='ADMIN' LIMIT 1")
        if not admin_user_id:
            admin_user_id = await conn.fetchval("SELECT id FROM users LIMIT 1")
        await conn.close()
    except Exception as e:
        print('Failed to fetch user id:', e)
        return
    if not admin_user_id:
        print('No users found in database. Cannot proceed.')
        return
    print('Using user id:', admin_user_id)

    tracker = EnhancedDatabaseAuditTracker(session_type='serper_test', user_id=admin_user_id, blog_id=None)
    await tracker.start_session()
    tm = ToolsManager(audit_tracker=tracker)
    print('SERPER_API_KEY set length:', len(key) if key else 'MISSING')
    tools = tm.get_research_tools()
    print('Research tools loaded:', [t.__class__.__name__ for t in tools])
    serper = None
    for t in tools:
        if 'Serper' in t.__class__.__name__:
            serper = t
            break
    if not serper:
        print('SerperDevTool not loaded')
    else:
        print('Calling SerperDevTool.run("OpenAI latest updates" ) ...')
        try:
            result = serper.run('OpenAI latest updates')
            print('Result keys:', result.keys() if isinstance(result, dict) else type(result))
            # Allow background logger thread time to persist llm_calls
            await asyncio.sleep(2)
        except Exception as e:
            print('Serper call error:', e)
    await tracker.end_session()

if __name__ == '__main__':
    asyncio.run(main())
