"""
Background tasks for newsletter generation
Uses Redis Queue (RQ) for asynchronous processing
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

# Add the parent directory to the path to import newsletter modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Create a simple mock for newsletter functionality
class MockNewsletterGenerator:
    def collect_articles(self, keywords=None, domain=None):
        """Mock article collection"""
        if keywords:
            articles = []
            for keyword in keywords.split(','):
                articles.append({
                    'title': f"Latest developments in {keyword.strip()}",
                    'summary': f"Recent news and insights about {keyword.strip()}...",
                    'url': f"https://example.com/{keyword.strip().replace(' ', '-')}",
                    'published': datetime.now().isoformat()
                })
            return articles
        elif domain:
            return [{
                'title': f"Insights into {domain}",
                'summary': f"Comprehensive analysis of {domain} trends and developments...",
                'url': f"https://example.com/{domain.replace(' ', '-')}",
                'published': datetime.now().isoformat()
            }]
        return []
    
    def summarize_articles(self, articles):
        """Mock article summarization"""
        return articles  # Return as-is for mock
    
    def compose_newsletter(self, articles, title="Newsletter"):
        """Mock newsletter composition"""
        html_content = f"<h1>{title}</h1>\n"
        html_content += f"<p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n"
        html_content += "<h2>Featured Articles</h2>\n"
        
        for i, article in enumerate(articles, 1):
            html_content += f"<h3>{i}. {article['title']}</h3>\n"
            html_content += f"<p>{article['summary']}</p>\n"
            if article.get('url'):
                html_content += f"<p><a href='{article['url']}'>Read more</a></p>\n"
            html_content += "<hr>\n"
        
        return html_content
    
    def send_newsletter_email(self, content, email, subject="Newsletter"):
        """Mock email sending"""
        print(f"Mock: Would send email to {email} with subject '{subject}'")
        return True

# Initialize mock generator
newsletter_generator = MockNewsletterGenerator()

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'storage.db')

def update_job_status(job_id, status, result=None):
    """Update job status in database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if result:
        cursor.execute(
            'UPDATE history SET status = ?, result = ? WHERE id = ?',
            (status, json.dumps(result), job_id)
        )
    else:
        cursor.execute(
            'UPDATE history SET status = ? WHERE id = ?',
            (status, job_id)
        )
    
    conn.commit()
    conn.close()

def generate_newsletter_task(params, job_id):
    """
    Background task to generate newsletter
    This function will be called by Redis Queue worker
    """
    try:
        update_job_status(job_id, 'processing')
        
        # Step 1: Collect articles
        if 'keywords' in params:
            articles = newsletter_generator.collect_articles(keywords=params['keywords'])
        elif 'domain' in params:
            articles = newsletter_generator.collect_articles(domain=params['domain'])
        else:
            raise ValueError("Either keywords or domain must be provided")
        
        if not articles:
            raise ValueError("No articles found for the given criteria")
        
        # Step 2: Summarize articles
        summarized_articles = newsletter_generator.summarize_articles(articles)
        
        # Step 3: Compose newsletter
        title = generate_subject(params)
        html_content = newsletter_generator.compose_newsletter(summarized_articles, title)
        
        # Step 4: Send email if requested
        email_sent = False
        if params.get('email') and not params.get('preview_only'):
            email_sent = newsletter_generator.send_newsletter_email(
                html_content, 
                params['email'], 
                title
            )
        
        # Step 5: Handle scheduling if requested
        if params.get('schedule') and params.get('rrule'):
            create_schedule_entry(params, job_id)
        
        result = {
            'html_content': html_content,
            'articles_count': len(summarized_articles),
            'email_sent': email_sent,
            'subject': title,
            'created_at': datetime.now().isoformat()
        }
        
        update_job_status(job_id, 'completed', result)
        return result
        
    except Exception as e:
        error_result = {'error': str(e)}
        update_job_status(job_id, 'failed', error_result)
        raise

def generate_subject(params):
    """Generate newsletter subject based on parameters"""
    if 'keywords' in params:
        keywords = params['keywords']
        if isinstance(keywords, list):
            keywords_str = ', '.join(keywords[:3])  # First 3 keywords
        else:
            keywords_str = keywords
        return f"Newsletter: {keywords_str}"
    elif 'domain' in params:
        return f"Newsletter: {params['domain']} Insights"
    else:
        return f"Newsletter - {datetime.now().strftime('%Y-%m-%d')}"

def create_schedule_entry(params, job_id):
    """Create a scheduled newsletter entry"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Calculate next run time (simplified - would use proper RRULE parsing in production)
    from datetime import timedelta
    next_run = datetime.now() + timedelta(days=7)  # Default to weekly
    
    cursor.execute('''
        INSERT INTO schedules (id, params, rrule, next_run)
        VALUES (?, ?, ?, ?)
    ''', (schedule_id, json.dumps(params), params.get('rrule', 'FREQ=WEEKLY'), next_run))
    
    conn.commit()
    conn.close()
    
    return schedule_id
        print(f"Error summarizing articles: {e}")
        return articles

def compose_newsletter_html(articles, params):
    """Compose newsletter HTML"""
    try:
        subject = generate_subject(params)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .newsletter {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 30px; }}
                .article {{ margin-bottom: 30px; padding: 20px; border-left: 4px solid #007bff; background: #f8f9fa; }}
                .article h3 {{ margin-top: 0; color: #007bff; }}
                .article .meta {{ color: #666; font-size: 0.9em; margin-bottom: 10px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="newsletter">
                <div class="header">
                    <h1>{subject}</h1>
                    <p>생성일: {datetime.now().strftime('%Y년 %m월 %d일')}</p>
                </div>
        """
        
        for i, article in enumerate(articles, 1):
            html_content += f"""
                <div class="article">
                    <h3>{i}. {article['title']}</h3>
                    <div class="meta">
                        출처: {article.get('source', 'Unknown')} | 
                        발행일: {article.get('published_date', 'Unknown')}
                    </div>
                    <p>{article['summary']}</p>
                    {f'<p><a href="{article["url"]}" target="_blank">원문 보기</a></p>' if article.get('url') else ''}
                </div>
            """
        
        html_content += """
                <div class="footer">
                    <p>이 뉴스레터는 Newsletter Generator를 통해 자동 생성되었습니다.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        print(f"Error composing newsletter: {e}")
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

def send_newsletter_email_task(email, html_content, params):
    """Send newsletter via email"""
    try:
        subject = generate_subject(params)
        
        # This should integrate with the actual email sending function
        # For now, just log the attempt
        print(f"Sending email to: {email}")
        print(f"Subject: {subject}")
        print(f"Content length: {len(html_content)} characters")
        
        # Mock email sending success
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def create_schedule_entry(params, job_id):
    """Create schedule entry for recurring newsletters"""
    try:
        schedule_id = f"sched_{job_id}"
        
        # Calculate next run time based on RRULE
        # For now, using mock next run time
        next_run = datetime.now().isoformat()
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO schedules (id, params, rrule, next_run) VALUES (?, ?, ?, ?)',
            (schedule_id, json.dumps(params), params['rrule'], next_run)
        )
        conn.commit()
        conn.close()
        
        print(f"Created schedule entry: {schedule_id}")
        return schedule_id
    except Exception as e:
        print(f"Error creating schedule: {e}")
        return None

def generate_subject(params):
    """Generate email subject based on parameters"""
    if 'keywords' in params:
        keywords_str = ', '.join(params['keywords'][:3])  # Limit to first 3 keywords
        return f"뉴스레터: {keywords_str} 관련 최신 동향"
    elif 'domain' in params:
        return f"뉴스레터: {params['domain']} 분야 트렌드"
    else:
        return "뉴스레터: 최신 뉴스 모음"

# Worker entry point for RQ
if __name__ == '__main__':
    # This can be used to test tasks locally
    test_params = {
        'keywords': ['AI', '머신러닝'],
        'email': 'test@example.com'
    }
    result = generate_newsletter_task(test_params, 'test-job-id')
    print("Task result:", result)
