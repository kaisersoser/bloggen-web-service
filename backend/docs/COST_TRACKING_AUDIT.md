# Cost Tracking & Audit System

## 🎯 **Overview**

This system provides comprehensive audit tracking for blog generation costs, storing all LLM calls and expenses in the database for detailed analytics and admin oversight.

## 📊 **Features**

### **Database Audit Tracking (Permanent)**
- **Persistent Storage**: All LLM calls and costs stored in database
- **Admin Analytics**: Visual dashboard with charts and breakdowns
- **Audit Trail**: Costs preserved even if blogs are deleted
- **User Attribution**: Links costs to users and blogs
- **Phase Tracking**: Breakdown by generation phase (research, content, etc.)

### **Console Cost Tracking (Temporary)**
- **Real-time Output**: Prints cost estimates to server console
- **Development Insight**: Immediate feedback during development
- **Easy Removal**: Can be disabled without affecting database audit

## 🏗️ **Database Schema**

### **AuditSession**
```sql
- id: Unique session identifier
- blogId: Associated blog (nullable)
- userId: User who triggered the generation
- sessionType: 'blog_generation', 'title_generation', etc.
- totalCost, totalTokens, callCount: Aggregated metrics
- startTime, endTime: Session duration
```

### **LLMCall**
```sql
- id: Unique call identifier
- auditSessionId: Parent session
- model, phase, agentRole: Call classification
- inputTokens, outputTokens, costs: Usage metrics
- callType: 'estimated' or 'actual'
```

## 🔧 **Integration Points**

### **Backend Integration**
1. **Title Generation** (`main.py`): Tracks OpenAI title generation
2. **Blog Flow** (`flows.py`): Tracks all CrewAI agent costs
3. **API Endpoints**: Admin audit analytics endpoints

### **Frontend Integration**
1. **Admin Dashboard** (`/admin/audit`): Visual analytics interface
2. **API Routes**: Fetch and display audit data
3. **Charts**: Cost trends, phase breakdowns, model usage

## 📈 **Admin Dashboard Features**

### **Cost Analytics**
- **Time Series**: Daily cost trends over time
- **Phase Breakdown**: Costs by generation phase (pie chart)
- **Model Usage**: Costs by AI model (bar chart)
- **User Roles**: Costs by user tier (pie chart)

### **Summary Metrics**
- Total costs, tokens, API calls, sessions
- Average cost per session and per token
- Date range filtering (7, 30, 90 days)

### **Detailed Views**
- Individual session breakdowns
- Per-phase cost analysis
- Model-specific usage patterns

## 🚀 **Access Instructions**

### **Admin Dashboard**
1. **Login** as an ADMIN user
2. **Navigate** to `/admin/audit`
3. **View** comprehensive cost analytics
4. **Filter** by date range (7, 30, 90 days)

### **Database Access**
1. **Prisma Studio**: `npm run db:studio` (port 5555)
2. **Direct Query**: Use Prisma client in API routes
3. **Database Browser**: View AuditSession and LLMCall tables

## 💾 **Data Persistence**

### **Audit Data Retention**
- **Blog Deletion**: Audit data is **preserved** even if blogs are deleted
- **User Deletion**: Audit data is **preserved** for compliance
- **Session Tracking**: Complete audit trail maintained
- **Cost History**: Full cost history for operational insights

### **Database Relationships**
- **AuditSession** ↔ **User**: Many-to-one (preserved on user deletion)
- **AuditSession** ↔ **Blog**: Many-to-one (preserved on blog deletion)
- **LLMCall** ↔ **AuditSession**: Many-to-one (cascade delete)

## 🔧 **Configuration**

### **Cost Estimation**
- **Models**: Pricing for GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, GPT-4o variants
- **Token Estimation**: ~4 characters per token for output estimation
- **Input Tokens**: ~1000 tokens per agent for prompts and context

### **Phase Mapping**
- **research_phase**: Research agent operations
- **content_generation_phase**: Content creation and image integration
- **fact_checking_phase**: Fact verification and accuracy
- **finalization_phase**: Final editing and formatting
- **title_generation**: Title creation API calls

## 🛠️ **Removing Console Cost Tracking (If Needed)**

If you want to remove the temporary console cost tracking while keeping database audit:

### **Step 1: Remove Imports**
```python
# Remove from flows.py
from .cost_tracker import CostTracker

# Remove from main.py  
from bloggen.cost_tracker import CostTracker
```

### **Step 2: Remove Console Tracking Code**
```python
# Remove from flows.py
self.cost_tracker = CostTracker("blog_generation")
self.cost_tracker.estimate_crew_cost(...)
self.cost_tracker.print_cost_summary()

# Remove from main.py
title_cost_tracker = CostTracker("title_generation")
title_cost_tracker.estimate_title_generation_cost()
title_cost_tracker.print_cost_summary()
```

### **Step 3: Keep Database Audit**
```python
# Keep in flows.py and main.py
from .audit_tracker import DatabaseCostTracker
# Keep all database audit tracking code
```

## 📋 **Cost Insights**

### **Typical Blog Generation Costs**
- **Research Phase**: ~$0.002-0.005 per blog
- **Content Generation**: ~$0.005-0.015 per blog  
- **Fact Checking**: ~$0.002-0.008 per blog
- **Finalization**: ~$0.001-0.004 per blog
- **Total per Blog**: ~$0.010-0.032 per blog

### **Pricing Optimization**
- **Free Tier** (20 blogs): ~$0.20-0.64 in costs
- **Plus Tier** (100 blogs): ~$1.00-3.20 in costs
- **Monthly Revenue**: $3.99 Plus tier
- **Gross Margin**: ~85-95% on Plus tier

## 🔐 **Security & Access**

### **Admin Only Features**
- Audit dashboard requires ADMIN role
- API endpoints check user permissions
- Database access restricted to authorized users

### **Data Privacy**
- User attribution for cost tracking
- No sensitive content stored in audit logs
- Compliance with data retention policies

---

## 💡 **Usage Examples**

### **Check User's Monthly Costs**
```sql
SELECT SUM(totalCost) as monthly_cost 
FROM AuditSession 
WHERE userId = 'user_id' 
AND createdAt >= date_trunc('month', CURRENT_DATE);
```

### **Most Expensive Generation Phases**
```sql
SELECT phase, SUM(totalCost) as phase_cost
FROM LLMCall 
GROUP BY phase 
ORDER BY phase_cost DESC;
```

### **Daily Cost Trends**
```sql
SELECT DATE(createdAt) as day, SUM(totalCost) as daily_cost
FROM AuditSession 
GROUP BY DATE(createdAt) 
ORDER BY day DESC;
```

This comprehensive audit system provides full visibility into your blog generation costs while supporting data-driven pricing decisions! 📊💰
