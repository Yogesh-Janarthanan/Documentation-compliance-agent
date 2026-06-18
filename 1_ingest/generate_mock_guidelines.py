"""
generate_mock_guidelines.py
Generates a stand-in WaiverPro guidelines PDF (official one was unavailable).
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

OUTPUT_PATH = "WaiverPro_User_Guidelines_MOCK.pdf"

doc = SimpleDocTemplate(OUTPUT_PATH, pagesize=letter,
                         topMargin=0.75 * inch, bottomMargin=0.75 * inch)
styles = getSampleStyleSheet()

h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=12)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceAfter=8, spaceBefore=14)
body = ParagraphStyle("body", parent=styles["Normal"], spaceAfter=8, leading=15)
note = ParagraphStyle("note", parent=styles["Italic"], spaceAfter=8, textColor=colors.grey)

story = []

story.append(Paragraph("WaiverPro User Guidelines", h1))
story.append(Paragraph(
    "<i>NOTE: This document is a reconstructed stand-in guideline since the "
    "official guidelines PDF was not provided for this assignment.</i>", note))
story.append(Spacer(1, 12))

story.append(Paragraph("Section 1: Overview", h2))
story.append(Paragraph(
    "WaiverPro is a Healthcare Waiver Management platform that streamlines "
    "regulatory waiver processes, from submission through approval. "
    "Facilities use WaiverPro to apply for and track three categories of "
    "waivers: Patient Needs Waiver (PNW), Program Flexibility (PF), and "
    "Workforce Shortage Waiver (WSW).", body))

story.append(Paragraph("Section 2: Accessing WaiverPro", h2))
story.append(Paragraph(
    "Users access their WaiverPro account by navigating to the login page "
    "and entering their registered email address and password. The login "
    "button should be labeled <b>'Sign In'</b> to align with platform-wide "
    "terminology used across all WaiverPro touchpoints.", body))
story.append(Paragraph(
    "The email field placeholder should display the example format "
    "<b>'name@company.com'</b> to reinforce that business email addresses "
    "are required for registration.", body))

story.append(Paragraph("Section 3: Patient Needs Waiver (PNW) Request", h2))
story.append(Paragraph(
    "Facilities may apply when seeking a waiver of the 24-hour CNA "
    "requirement to meet individual patient care plan modifications based "
    "on clinical needs. Applications require documented patient or family "
    "request for accommodation modification, along with clinical assessment "
    "supporting that the modification must be care-specific. Interdisciplinary "
    "team agreement and approval is required prior to submission.", body))
story.append(Paragraph(
    "<b>Processing Time:</b> 10-20 business days. <b>Waiver Period:</b> 6-12 months.", body))

story.append(Paragraph("Section 4: Program Flexibility (PF) Request", h2))
story.append(Paragraph(
    "Facilities seeking program flexibility from regulations must include "
    "justification for the program flexibility being sought, an adequate "
    "description of the alternative measures, and documentation supporting "
    "that patient care will not be compromised. Facilities may request "
    "program flexibility for a limited term with a start and end date; "
    "applications submitted more than one year in advance will not be "
    "accepted.", body))
story.append(Paragraph(
    "<b>Processing Time:</b> Within 60 days. <b>Waiver Period:</b> 6-12 months.", body))

story.append(Paragraph("Section 5: Workforce Shortage Waiver (WSW) Request", h2))
story.append(Paragraph(
    "Facilities seeking a waiver of the 3:1 direct care hour requirement due "
    "to a documented shortage of available and appropriate health care "
    "professionals and direct care givers may apply. Facilities may only "
    "submit one Patient Needs Waiver and one Workforce Shortage Waiver "
    "application in the same year. Applications must be submitted within "
    "the annual application window of January 1 - April 30.", body))
story.append(Paragraph(
    "Only licensed freestanding SNFs (excluding district, state-owned "
    "hospitals and developmental centers) may apply. Approved facilities "
    "must include an expiration date and specific terms; renewal may be "
    "required if conditions are not met.", body))

story.append(Paragraph("Section 6: My Applications Dashboard", h2))
story.append(Paragraph(
    "Once logged in, users land on the 'My Applications' dashboard, which "
    "displays a list of all waiver applications submitted by the facility, "
    "along with their current status (e.g. Pending, Approved, Denied, "
    "Expired). Each application entry should display the waiver type, "
    "submission date, and a unique application reference number.", body))

story.append(Paragraph("Section 7: User Management", h2))
story.append(Paragraph(
    "Administrators can manage facility user accounts from the User "
    "Management page, including adding new users, editing roles and "
    "permissions, and deactivating accounts that should no longer have "
    "access. All role changes must be logged for audit purposes.", body))

story.append(Paragraph("Section 8: Support and Contact Information", h2))
story.append(Paragraph(
    "Users requiring assistance can reach the WaiverPro support team via "
    "the Contact page. The official support email listed should be "
    "<b>support@waiverpro.com</b> and the support phone line should be "
    "available Monday through Friday, 9 AM to 5 PM.", body))

story.append(Paragraph("Section 9: Privacy Policy and Terms of Service", h2))
story.append(Paragraph(
    "WaiverPro's Privacy Policy and Terms of Service are accessible from "
    "the footer of every page, including the public landing page. These "
    "documents must be reviewed and accepted during account registration.", body))

doc.build(story)
print(f"Mock guidelines PDF created at: {OUTPUT_PATH}")