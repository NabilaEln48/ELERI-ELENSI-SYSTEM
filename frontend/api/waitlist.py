import json
import os
import psycopg
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_POST(self):
        try:
            # 1. Parse Request Data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            # 2. Get Database URL (Ensure .env is loaded in your environment)
            db_url = os.getenv("WAITLIST_DATABASE_URL")
            if not db_url:
                raise ValueError("Database connection string is missing.")

            # 3. Clean Input Data
            email = data.get('email', '').strip().lower()
            
            # 4. Connect and Execute
            # Using connect_timeout to handle Neon's scale-to-zero wake-up time
            with psycopg.connect(db_url, connect_timeout=15) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO Waitlist (
                            email, 
                            first_name, 
                            last_name, 
                            linkedin_profile_url,
                            linkedin_post_url, 
                            referral_source, 
                            position_level,
                            target_market, 
                            looking_for,
                            created_at,
                            updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                        ON CONFLICT (email)
                        DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            linkedin_post_url = EXCLUDED.linkedin_post_url,
                            looking_for = EXCLUDED.looking_for,
                            updated_at = now()
                    """, (
                        email,
                        data.get('first_name'),
                        data.get('last_name'),
                        data.get('linkedin_profile_url'),
                        data.get('linkedin_post_url'),
                        data.get('referral_source', 'Website'),
                        data.get('position_level'),
                        data.get('target_market'),
                        data.get('looking_for')  # Passed as a Python list
                    ))
                conn.commit()
            
            # 5. Success Response
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))

        except Exception as e:
            # 6. Error Handling
            self._set_headers(500)
            # Log the full error to your server console for debugging
            print(f"Error: {str(e)}")
            
            # Return a cleaner message to the user
            clean_error = "Connection timeout. Please try again." if "connection failed" in str(e).lower() else str(e)
            self.wfile.write(json.dumps({"error": clean_error}).encode('utf-8'))