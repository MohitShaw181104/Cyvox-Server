from fastapi import APIRouter, status, HTTPException, Form
from app.utils.email_sender import send_confirmation_email

router = APIRouter()

@router.post("/mail", status_code=status.HTTP_200_OK, summary="Send test email confirmation")
async def test_email_endpoint(
    email: str = Form(...),
    username: str = Form(...),
    complaint_id: str = Form(...)
):
    try:
        send_confirmation_email(email, username, complaint_id)
        return {"message": f"Email successfully sent to {email}"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to send email: {str(e)}"}
        )

mail_router = router