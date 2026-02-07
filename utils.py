import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import google.generativeai as genai

# Mock Email Function for Prototype
def send_supplier_email(supplier_email, product_name, quantity, owner_name):
    """
    Sends an email to a supplier using credentials from st.secrets.
    """
    email_sender = None
    email_password = None
    
    try:
        email_sender = st.secrets["EMAIL_ADDRESS"]
        email_password = st.secrets["EMAIL_PASSWORD"]
    except Exception:
        # Fallback for prototype if secrets are not set
        print("Secrets for email not found. Using Mock.")
    
    subject = f"Order Request: {product_name}"
    body = f"""
    Dear Supplier,
    
    We would like to place an order for the following:
    
    Product: {product_name}
    Quantity: {quantity}
    
    Please confirm availability and delivery date.
    
    Best regards,
    {owner_name}
    """
    
    if email_sender and email_password:
        try:
            msg = MIMEMultipart()
            msg['From'] = email_sender
            msg['To'] = supplier_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to Gmail SMTP server
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(email_sender, email_password)
            server.send_message(msg)
            server.quit()
            return True, f"Email sent to {supplier_email}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    else:
        # PROTOTYPE: Just print to console or return success string
        print(f"--- MOCK EMAIL SENT TO {supplier_email} ---")
        print(subject)
        print(body)
        print("-------------------------------------------")
        return True, "Email sent successfully (Mock Mode - Configure secrets for real email)"

def get_ai_response(prompt, api_key=None):
    """
    Get response from AI model.
    """
    if not api_key:
        return "AI Chatbot is not configured with an API Key. Please provide one to use this feature."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Simple safety check if prompt is empty
        if not prompt.strip():
            return "Please enter a question."

        response = model.generate_content(prompt)
        
        # Check if response has content (sometimes blocking filters return empty)
        if response.text:
            return response.text
        else:
            return "I'm sorry, I couldn't generate a response for that prompt."
            
    except Exception as e:
        return f"Error communicating with AI: {str(e)}"
