import logging
import os
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
import asyncio
from datetime import datetime, timedelta
import time

import traceback
from keep_alive import run_flask, ping_server
from threading import Thread

# Add GitHub storage import
from github_storage import init_github_storage, load_materials, save_materials

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced error handler with detailed logging"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Get detailed error information
    error_traceback = traceback.format_exc()
    logger.error(f"Full error traceback:\n{error_traceback}")
    
    # Send a more specific error message to the user
    if update and update.effective_chat:
        text = "❌ Sorry, an error occurred. The issue has been logged and will be fixed soon."
        try:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        except Exception as e:
            logger.error(f"Could not send error message: {e}")

# Import configuration
import config

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define states for conversation
(
    START,
    ADMIN_STATS,
    TOGGLE_ADS,
    AD_STATS,
    BRANCH_SELECTION,
    SEMESTER_SELECTION,
    SUBJECT_SELECTION,
    MATERIAL_SELECTION,
    ADMIN_UPLOAD,
    SEARCH_RESULTS,
    UPLOAD_FILE,      # NEW: For team member file upload
    UPLOAD_DETAILS,   # NEW: For team member upload details
    GITHUB_STATUS,
    STORAGE,
    FORCE_SAVE
    
) = range(15)

# Ensure PDF folder exists
if not os.path.exists(config.PDF_FOLDER):
    os.makedirs(config.PDF_FOLDER)

# def load_materials():
#     """Load study materials from JSON file."""
#     try:
#         if os.path.exists(config.DATA_FILE):
#             with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
#                 return json.load(f)
#         else:
#             # Create initial file with sample data
#             initial_data = {
#                 "CSE": {
#                     "4": {
#                         "DBMS": {
#                             "materials": [
#                                 {"title": "DBMS Module 2 Notes", "file_id": "", "type": "pdf", "keywords": ["dbms", "database", "module2"]},
#                             ]
#                         }
#                     }
#                 }
#             }
#             save_materials(initial_data)
#             return initial_data
#     except Exception as e:
#         logger.error(f"Error loading materials: {e}")
#         return {}

# def save_materials(materials):
#     """Save study materials to JSON file."""
#     try:
#         with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
#             json.dump(materials, f, indent=2, ensure_ascii=False)
#     except Exception as e:
#         logger.error(f"Error saving materials: {e}")

# Load materials at startup
STUDY_MATERIALS = load_materials()

def search_materials(query):
    """Search materials by keyword."""
    query = query.lower().strip()
    results = []
    
    for branch, semesters in STUDY_MATERIALS.items():
        for semester, subjects in semesters.items():
            for subject, data in subjects.items():
                for material in data.get("materials", []):
                    # Search in title
                    if query in material["title"].lower():
                        results.append({
                            "branch": branch,
                            "semester": semester,
                            "subject": subject,
                            "material": material
                        })
                    # Search in keywords
                    elif any(query in keyword for keyword in material.get("keywords", [])):
                        results.append({
                            "branch": branch,
                            "semester": semester,
                            "subject": subject,
                            "material": material
                        })
                    # Search in subject name
                    elif query in subject.lower():
                        results.append({
                            "branch": branch,
                            "semester": semester,
                            "subject": subject,
                            "material": material
                        })
    
    return results

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send greeting message and show main menu options."""
    user = update.effective_user
    user_role = get_user_role(user.id)

    # Check if user is admin
    if user.id in config.ADMIN_IDS:
        welcome_text = (
            f"👋 Welcome Admin {user.first_name}! 📚\n\n"
            "You have administrative privileges. "
            "Please choose an option below:"
        )
        # Full admin menu
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search", callback_data="search"),
                InlineKeyboardButton("📂 Browse", callback_data="browse"),
            ],
            [
                InlineKeyboardButton("📤 Upload Material", callback_data="upload_menu"),
                InlineKeyboardButton("👥 Manage Team", callback_data="manage_team"),
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
                InlineKeyboardButton("❤️ Donate", callback_data="donate"),
            ],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        ]
    elif user.id in config.TEAM_MEMBER_IDS:
        welcome_text = (
            f"👋 Welcome Member {user.first_name}! 📚\n\n"
            "You have Member privileges. "
            "Please choose an option below:"
        )
        # Team member menu (upload access only)
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search", callback_data="search"),
                InlineKeyboardButton("📂 Browse", callback_data="browse"),
            ],
            [InlineKeyboardButton("📤 Upload Material", callback_data="upload_menu")],
            [
                InlineKeyboardButton("❤️ Donate", callback_data="donate"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help"),
            ],
        ]
    else:
        welcome_text = (
            f"👋 Welcome {user.first_name} to the Study Material Bot! 📚\n\n"
            "I'm here to help you find study materials for your courses. "
            "Please choose an option below:"
        )
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search", callback_data="search"),
                InlineKeyboardButton("📂 Browse by Branch", callback_data="browse"),
            ],
            [
                InlineKeyboardButton("❤️ Donate", callback_data="donate"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help")
            ],
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    context.user_data['current_state'] = START
    return START

async def show_upload_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show upload menu for team members and admins"""
    user = update.effective_user
    
    if not is_team_member(user.id):
        await update.callback_query.edit_message_text("❌ Upload access required. Contact admin.")
        return await start(update, context)
    
    user_role = get_user_role(user.id)
    
    text = (
        f"📤 **Upload Materials** - {user_role}\n\n"
        "Please send the file (PDF, DOC, etc.) first, then I'll ask for details.\n\n"
        "📝 **Required details after file:**\n"
        "`Branch, Semester, Subject, Title, Keywords`\n\n"
        "**Example:**\n"
        "`CSE, 4, DBMS, DBMS Module 3 Notes, dbms module3 normalization`\n\n"
        "Click Cancel to go back."
    )
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="back_to_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return UPLOAD_FILE

async def handle_team_upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle file upload from team members"""
    user = update.effective_user
    
    if not is_team_member(user.id):
        await update.message.reply_text("❌ Upload access required.")
        return await start(update, context)
    
    if update.message.document:
        file = await update.message.document.get_file()
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
        file_size = update.message.document.file_size
        
        # Validate file type
        allowed_types = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.png']
        if not any(file_name.lower().endswith(ext) for ext in allowed_types):
            await update.message.reply_text("❌ Please upload PDF, Word, text, or image files only.")
            return UPLOAD_FILE
        
        # Validate file size (20MB limit)
        if file_size > 20 * 1024 * 1024:
            await update.message.reply_text("❌ File too large. Please upload files smaller than 20MB.")
            return UPLOAD_FILE
        
        # Store file info in context
        context.user_data["upload_file_id"] = file_id
        context.user_data["upload_file_name"] = file_name
        context.user_data["upload_file_type"] = "document"
        
        # # Download file to local storage for backup
        # try:
        #     downloaded_file = await file.download_to_drive(f"{config.PDF_FOLDER}{file_name}")
        #     logger.info(f"✅ File saved by {user.first_name}: {downloaded_file}")
        # except Exception as e:
        #     logger.error(f"❌ Error saving file: {e}")
        #     await update.message.reply_text("⚠️ File received but could not save locally. Continuing...")
        
        text = (
            f"✅ **File Received!**\n\n"
            f"📄 **File:** {file_name}\n"
            f"👤 **Uploaded by:** {user.first_name}\n\n"
            f"📝 **Now please send the details in this format:**\n"
            "`Branch, Semester, Subject, Title, Keywords`\n\n"
            "**Example:**\n"
            "`CSE, 4, DBMS, DBMS Module 3 Notes, dbms module3 normalization`\n\n"
            "💡 **Tips:**\n"
            "- Use exact branch names: CSE, ECE, EEE, Mech, Civil\n"
            "- Semester must be 1-8\n"
            "- Add multiple keywords for better search"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        return UPLOAD_DETAILS
    else:
        await update.message.reply_text("❌ Please send a file (PDF, Word, etc.)")
        return UPLOAD_FILE

async def handle_team_upload_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text input during team member upload with enhanced debugging"""
    user = update.effective_user
    
    if not is_team_member(user.id):
        await update.message.reply_text("❌ Upload access required.")
        return await start(update, context)
    
    # Check if file was uploaded first
    if "upload_file_id" not in context.user_data:
        await update.message.reply_text("❌ Please send the file first, then the details.")
        return UPLOAD_DETAILS
    
    try:
        # Parse the details
        parts = [part.strip() for part in update.message.text.split(',')]
        if len(parts) < 5:
            raise ValueError("❌ Not enough details. Need: Branch, Semester, Subject, Title, Keywords")
        
        branch, semester, subject, title = parts[0], parts[1], parts[2], parts[3]
        keywords = [k.strip().lower() for k in parts[4:]]
        
        # Validate inputs
        valid_branches = ["CSE", "ECE", "EEE", "Mech", "Civil"]
        if branch not in valid_branches:
            raise ValueError(f"❌ Invalid branch: {branch}. Use: {', '.join(valid_branches)}")
        
        if not semester.isdigit() or not (1 <= int(semester) <= 8):
            raise ValueError("❌ Invalid semester. Use a number between 1-8")
        
        if not subject.strip():
            raise ValueError("❌ Subject cannot be empty")
        if not title.strip():
            raise ValueError("❌ Title cannot be empty")
        if not keywords:
            raise ValueError("❌ Please provide at least one keyword")
        
        print(f"🔄 Processing upload: {branch}, Sem {semester}, {subject}, '{title}'")
        
        # CRITICAL: Ensure STUDY_MATERIALS is the global variable
        global STUDY_MATERIALS
        
        # Create structure if not exists
        if branch not in STUDY_MATERIALS:
            STUDY_MATERIALS[branch] = {}
        if semester not in STUDY_MATERIALS[branch]:
            STUDY_MATERIALS[branch][semester] = {}
        if subject not in STUDY_MATERIALS[branch][semester]:
            STUDY_MATERIALS[branch][semester][subject] = {"materials": []}
        
        # Add material
        new_material = {
            "title": title,
            "file_id": context.user_data["upload_file_id"],
            "type": context.user_data["upload_file_type"],
            "keywords": keywords,
            "uploaded_by": user.first_name,
            "uploaded_at": datetime.now().isoformat()
        }
        
        print(f"➕ Adding material to: {branch}/{semester}/{subject}")
        STUDY_MATERIALS[branch][semester][subject]["materials"].append(new_material)
        
        # CRITICAL: Count materials before save
        materials_count = len(STUDY_MATERIALS[branch][semester][subject]["materials"])
        print(f"📊 Material added. Now {materials_count} materials in {subject}")
        
        # Save to storage
        print("💾 Calling save_materials...")
        save_materials(STUDY_MATERIALS)
        print("✅ save_materials completed")
        
        # Verify the save worked by checking local file
        try:
            if os.path.exists('study_materials.json'):
                with open('study_materials.json', 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    saved_count = len(saved_data.get(branch, {}).get(semester, {}).get(subject, {}).get("materials", []))
                    print(f"🔍 VERIFICATION: Local file has {saved_count} materials for {subject}")
            else:
                print("❌ VERIFICATION: Local file not found after save!")
        except Exception as e:
            print(f"❌ VERIFICATION ERROR: {e}")
        
        # Success message
        text = (
            f"🎉 **Material Uploaded Successfully!**\n\n"
            f"👤 **Uploaded by:** {user.first_name}\n"
            f"🏛️ **Branch:** {branch}\n"
            f"📅 **Semester:** {semester}\n"
            f"📚 **Subject:** {subject}\n"
            f"📄 **Title:** {title}\n"
            f"🔍 **Keywords:** {', '.join(keywords)}\n\n"
            f"✅ The material is now available to users."
        )
        
        # Clear upload data
        context.user_data.pop("upload_file_id", None)
        context.user_data.pop("upload_file_name", None)
        context.user_data.pop("upload_file_type", None)
        
        keyboard = [
            [InlineKeyboardButton("📤 Upload Another", callback_data="upload_menu")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        context.user_data['current_state'] = START
        return START
        
    except Exception as e:
        error_text = (
            f"❌ **Error:** {str(e)}\n\n"
            "📝 **Please try again with this format:**\n"
            "`Branch, Semester, Subject, Title, Keywords`\n\n"
            "**Example:**\n"
            "`CSE, 4, DBMS, DBMS Module 3 Notes, dbms module3 normalization`\n\n"
            "💡 **Tips:**\n"
            "- Use exact branch names: CSE, ECE, EEE, Mech, Civil\n"
            "- Semester must be 1-8\n"
            "- Add multiple keywords for better search"
        )
        await update.message.reply_text(error_text, parse_mode="Markdown")
        return UPLOAD_DETAILS
    
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fixed button handler with error handling"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        logger.info(f"Button pressed: {data}")
        
        # Handle ad verification buttons FIRST
        if data.startswith("verify_download_") or data.startswith("check_status_"):
            await handle_verification(update, context)
            return START
        
        # Handle free downloads (both browse and search)
        if data.startswith("free_download"):
            await handle_free_download(update, context)
            return START
        
        # Handle status display
        if data == "show_my_status":
            await show_user_status(update, context)
            return START
        
        # Handle search results - CRITICAL FIX
        if data.startswith("search_result_"):
            result_index = int(data.replace("search_result_", ""))
            logger.info(f"Processing search result: {result_index}")
            return await show_search_result(update, context, result_index)
        
        # Handle material selection from browse
        if data.startswith("material_"):
            material_index = int(data.replace("material_", ""))
            logger.info(f"Processing material selection: {material_index}")
            return await select_material(update, context, material_index)
        
        # Then handle other navigation buttons
        if data == "browse":
            return await show_branches(update, context)
        elif data == "help":
            return await show_help(update, context)
        elif data == "search":
            return await start_search(update, context)
        elif data == "upload_menu":
            return await show_upload_menu(update, context)
        elif data == "donate":
            return await show_donation_options(update, context)
        elif data in ["copy_upi", "copy_btc", "donate_upi_qr"]:
            await handle_donation_buttons(update, context)
            return START
        elif data in ["CSE", "ECE", "EEE", "Mech", "Civil"]:
            context.user_data["branch"] = data
            return await show_semesters(update, context)
        elif data.isdigit() and 1 <= int(data) <= 8:
            context.user_data["semester"] = data
            return await show_subjects(update, context)
        elif data.startswith("subject_"):
            subject = data.replace("subject_", "")
            context.user_data["subject"] = subject
            return await show_materials(update, context)
        elif data == "back_to_start":
            return await start(update, context)
        elif data == "back_to_branches":
            return await show_branches(update, context)
        elif data == "back_to_semesters":
            return await show_semesters(update, context)
        elif data == "back_to_subjects":
            return await show_subjects(update, context)
        elif data == "back_to_search":
            return await show_search_results(update, context)
        
        # If we get here, it's an unknown button
        logger.warning(f"Unknown button data: {data}")
        await query.edit_message_text("❌ Unknown button action. Please try again.")
        return await start(update, context)
        
    except Exception as e:
        logger.error(f"Error in handle_button: {str(e)}")
        logger.error(traceback.format_exc())
        
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ Error processing button. Please try again.")
        return await start(update, context)

# ADD these admin command functions:
async def ad_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show ad performance statistics"""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    stats = load_ad_stats()
    
    text = "📊 **Ad Performance Report**\n\n"
    text += f"💰 **Total Revenue:** ${stats.get('revenue_earned', 0):.2f}\n"
    text += f"👁️ **Total Impressions:** {stats.get('total_impressions', 0)}\n"
    text += f"✅ **Total Conversions:** {stats.get('conversions', 0)}\n\n"
    
    text += "**Per Ad Performance:**\n"
    for ad_id, ad_data in stats.get('ad_clicks', {}).items():
        clicks = ad_data.get('clicks', 0)
        conversions = ad_data.get('conversions', 0)
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
        text += f"• {ad_id}: {clicks} clicks, {conversions} conversions ({conversion_rate:.1f}%)\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def toggle_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle ad system on/off"""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    config.AD_VERIFICATION_ENABLED = not config.AD_VERIFICATION_ENABLED
    status = "ENABLED" if config.AD_VERIFICATION_ENABLED else "DISABLED"
    
    await update.message.reply_text(f"✅ Ad verification system is now {status}")

# Admin upload functionality
async def start_admin_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the admin upload process with clear instructions."""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.callback_query.edit_message_text("❌ You don't have permission to upload materials.")
        return await start(update, context)
    
    text = (
        "📤 **Admin Upload Mode**\n\n"
        "📝 **How to upload:**\n"
        "1. First, send me the PDF file\n"
        "2. Then, send the details in this format:\n\n"
        "`Branch, Semester, Subject, Title, Keywords`\n\n"
        "🔸 **Example:**\n"
        "`CSE, 4, DBMS, DBMS Module 1 Notes, dbms database module1 rdbms`\n\n"
        "📋 **Available Branches:** CSE, ECE, EEE, Mech, Civil\n"
        "📅 **Semesters:** 1-8\n\n"
        "Click Cancel to go back."
    )
    
    keyboard = [[InlineKeyboardButton("❌ Cancel Upload", callback_data="back_to_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    context.user_data['current_state'] = ADMIN_UPLOAD
    return ADMIN_UPLOAD

async def handle_admin_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle file upload from admin with better feedback."""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to upload materials.")
        return await start(update, context)
    
    if update.message.document:
        file = await update.message.document.get_file()
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
        file_size = update.message.document.file_size
        
        # Validate file type
        if not file_name.lower().endswith('.pdf'):
            await update.message.reply_text("❌ Please upload PDF files only.")
            return ADMIN_UPLOAD
        
        # Validate file size (10MB limit)
        if file_size > 10 * 1024 * 1024:
            await update.message.reply_text("❌ File too large. Please upload files smaller than 10MB.")
            return ADMIN_UPLOAD
        
        # Store file info in context
        context.user_data["upload_file_id"] = file_id
        context.user_data["upload_file_name"] = file_name
        context.user_data["upload_file_type"] = "document"
        
        # Download file to local storage for backup
        try:
            downloaded_file = await file.download_to_drive(f"{config.PDF_FOLDER}{file_name}")
            logger.info(f"✅ File saved to: {downloaded_file}")
        except Exception as e:
            logger.error(f"❌ Error saving file: {e}")
            await update.message.reply_text("⚠️ File received but could not save locally. Continuing...")
        
        text = (
            f"✅ **File Received Successfully!**\n\n"
            f"📄 **File Name:** {file_name}\n"
            f"📏 **Size:** {file_size // 1024} KB\n"
            f"🆔 **File ID:** `{file_id}`\n\n"
            "📝 **Now please send the details in this format:**\n"
            "`Branch, Semester, Subject, Title, Keywords`\n\n"
            "🔸 **Example:**\n"
            "`CSE, 4, DBMS, DBMS Module 1 Notes, dbms database module1`\n\n"
            "💡 **Tip:** Add multiple keywords separated by commas for better search results."
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        return ADMIN_UPLOAD
    else:
        await update.message.reply_text("❌ Please send a PDF file.")
        return ADMIN_UPLOAD

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text input during admin upload with detailed validation."""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to upload materials.")
        return await start(update, context)
    
    # Check if file was uploaded first
    if "upload_file_id" not in context.user_data:
        await update.message.reply_text("❌ Please send the PDF file first, then the details.")
        return ADMIN_UPLOAD
    
    try:
        # Parse the details
        parts = [part.strip() for part in update.message.text.split(',')]
        if len(parts) < 5:
            raise ValueError("❌ Not enough details. Need: Branch, Semester, Subject, Title, Keywords")
        
        branch, semester, subject, title = parts[0], parts[1], parts[2], parts[3]
        keywords = [k.strip().lower() for k in parts[4:]]
        
        # Validate branch
        valid_branches = ["CSE", "ECE", "EEE", "Mech", "Civil"]
        if branch not in valid_branches:
            raise ValueError(f"❌ Invalid branch: {branch}. Use: {', '.join(valid_branches)}")
        
        # Validate semester
        if not semester.isdigit() or not (1 <= int(semester) <= 8):
            raise ValueError("❌ Invalid semester. Use a number between 1-8")
        
        # Validate other fields
        if not subject.strip():
            raise ValueError("❌ Subject cannot be empty")
        if not title.strip():
            raise ValueError("❌ Title cannot be empty")
        if not keywords:
            raise ValueError("❌ Please provide at least one keyword")
        
        # Create structure if not exists
        if branch not in STUDY_MATERIALS:
            STUDY_MATERIALS[branch] = {}
        if semester not in STUDY_MATERIALS[branch]:
            STUDY_MATERIALS[branch][semester] = {}
        if subject not in STUDY_MATERIALS[branch][semester]:
            STUDY_MATERIALS[branch][semester][subject] = {"materials": []}
        
        # Add material
        new_material = {
            "title": title,
            "file_id": context.user_data["upload_file_id"],
            "type": context.user_data["upload_file_type"],
            "keywords": keywords
        }
        
        STUDY_MATERIALS[branch][semester][subject]["materials"].append(new_material)
        save_materials(STUDY_MATERIALS)
        
        # Success message
        text = (
            f"🎉 **Material Uploaded Successfully!**\n\n"
            f"🏛️ **Branch:** {branch}\n"
            f"📅 **Semester:** {semester}\n"
            f"📚 **Subject:** {subject}\n"
            f"📄 **Title:** {title}\n"
            f"🔍 **Keywords:** {', '.join(keywords)}\n"
            f"🆔 **File ID:** `{context.user_data['upload_file_id']}`\n\n"
            "✅ The material is now available to users."
        )
        
        # Clear upload data
        context.user_data.pop("upload_file_id", None)
        context.user_data.pop("upload_file_name", None)
        context.user_data.pop("upload_file_type", None)
        
        keyboard = [
            [InlineKeyboardButton("📤 Upload Another", callback_data="admin_upload")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        context.user_data['current_state'] = START
        return START
        
    except Exception as e:
        error_text = (
            f"❌ **Error:** {str(e)}\n\n"
            "📝 **Please try again with this format:**\n"
            "`Branch, Semester, Subject, Title, Keywords`\n\n"
            "🔸 **Example:**\n"
            "`CSE, 4, DBMS, DBMS Module 1 Notes, dbms database module1`\n\n"
            "💡 **Tips:**\n"
            "- Use exact branch names: CSE, ECE, EEE, Mech, Civil\n"
            "- Semester must be 1-8\n"
            "- Add multiple keywords for better search"
        )
        await update.message.reply_text(error_text, parse_mode="Markdown")
        return ADMIN_UPLOAD
    
# Access Control System
def is_admin(user_id):
    """Check if user is full admin"""
    return user_id in config.ADMIN_IDS

def is_team_member(user_id):
    """Check if user is team member (upload access only)"""
    return user_id in config.TEAM_MEMBER_IDS or user_id in config.ADMIN_IDS

def get_user_role(user_id):
    """Get user role for display"""
    if is_admin(user_id):
        return "👑 Admin"
    elif is_team_member(user_id):
        return "👥 Team Member" 
    else:
        return "👤 User"

# Search functionality
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the search process."""
    text = "🔍 **Search Materials**\n\nPlease type what you're looking for:\n\nExamples:\n- `dbms module 1 notes`\n- `operating systems`\n- `cse 4 sem dbms`"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data['current_state'] = SEARCH_RESULTS
    return SEARCH_RESULTS

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle search query."""
    query = update.message.text
    results = search_materials(query)
    
    if not results:
        text = f"❌ No results found for: `{query}`\n\nTry different keywords or browse by branch."
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search Again", callback_data="search"),
                InlineKeyboardButton("📂 Browse by Branch", callback_data="browse"),
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        context.user_data['current_state'] = START
        return START
    
    # Store results in context for navigation
    context.user_data["search_results"] = results
    context.user_data["search_query"] = query
    
    return await show_search_results(update, context)

async def show_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show search results."""
    results = context.user_data.get("search_results", [])
    query = context.user_data.get("search_query", "")
    
    text = f"🔍 Search results for: `{query}`\n\n**Found {len(results)} results:**\n\n"
    
    keyboard = []
    for i, result in enumerate(results[:10]):  # Show first 10 results
        material = result["material"]
        btn_text = f"{i+1}. {material['title']} ({result['branch']} Sem {result['semester']})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"search_result_{i}")])
    
    keyboard.append([
        InlineKeyboardButton("🔍 New Search", callback_data="search"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start"),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    context.user_data['current_state'] = SEARCH_RESULTS
    return SEARCH_RESULTS

async def show_search_result(update: Update, context: ContextTypes.DEFAULT_TYPE, result_index: int):
    """Fixed search result handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        logger.info(f"show_search_result called with index: {result_index}")
        
        results = context.user_data.get("search_results", [])
        logger.info(f"Total search results: {len(results)}")
        
        if result_index >= len(results):
            await query.edit_message_text("❌ Result not found.")
            return await start(update, context)
        
        result = results[result_index]
        material = result["material"]
        
        logger.info(f"Selected result: {material.get('title')}")
        
        # Store search context
        context.user_data["branch"] = result["branch"]
        context.user_data["semester"] = result["semester"] 
        context.user_data["subject"] = result["subject"]
        
        # Find material index in actual database
        materials = STUDY_MATERIALS.get(result["branch"], {}).get(result["semester"], {}).get(result["subject"], {}).get("materials", [])
        logger.info(f"Found {len(materials)} materials in database")
        
        material_index = -1
        for idx, mat in enumerate(materials):
            if mat.get("title") == material.get("title"):
                material_index = idx
                break
        
        logger.info(f"Material index in database: {material_index}")
        
        if material_index == -1:
            await query.edit_message_text("❌ Material not found in database.")
            return await start(update, context)
        
        # Use ad verification system
        return await select_material(update, context, material_index)
        
    except Exception as e:
        logger.error(f"Error in show_search_result: {str(e)}")
        logger.error(traceback.format_exc())
        
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ Error loading search result. Please try again.")
        return await start(update, context)

# Navigation functions
async def show_branches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show available branches."""
    text = "🎓 Please select your branch:"
    
    keyboard = [
        [
            InlineKeyboardButton("💻 CSE", callback_data="CSE"),
            InlineKeyboardButton("📡 ECE", callback_data="ECE"),
        ],
        [
            InlineKeyboardButton("⚡ EEE", callback_data="EEE"),
            InlineKeyboardButton("🔧 Mech", callback_data="Mech"),
        ],
        [
            InlineKeyboardButton("🏗️ Civil", callback_data="Civil"),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_start"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data['current_state'] = BRANCH_SELECTION
    return BRANCH_SELECTION

async def show_semesters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show available semesters for the selected branch."""
    branch = context.user_data.get("branch", "Unknown")
    text = f"📅 Please select your semester for {branch}:"
    
    keyboard = []
    for i in range(0, 8, 2):
        row = []
        if i+1 <= 8:
            row.append(InlineKeyboardButton(f"Sem {i+1}", callback_data=str(i+1)))
        if i+2 <= 8:
            row.append(InlineKeyboardButton(f"Sem {i+2}", callback_data=str(i+2)))
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🔙 Back to Branches", callback_data="back_to_branches"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start"),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data['current_state'] = SEMESTER_SELECTION
    return SEMESTER_SELECTION

async def show_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show available subjects for the selected branch and semester."""
    branch = context.user_data.get("branch", "Unknown")
    semester = context.user_data.get("semester", "Unknown")
    
    subjects = STUDY_MATERIALS.get(branch, {}).get(semester, {})
    
    if not subjects:
        text = f"❌ No subjects available for {branch} Semester {semester}."
        keyboard = [
            [
                InlineKeyboardButton("🔙 Back to Semesters", callback_data="back_to_semesters"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start"),
            ]
        ]
    else:
        text = f"📚 Available subjects for {branch} Semester {semester}:"
        keyboard = []
        
        for subject in subjects.keys():
            keyboard.append([InlineKeyboardButton(f"📖 {subject}", callback_data=f"subject_{subject}")])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Semesters", callback_data="back_to_semesters"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start"),
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data['current_state'] = SUBJECT_SELECTION
    return SUBJECT_SELECTION

async def show_materials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show available materials for the selected subject."""
    branch = context.user_data.get("branch", "Unknown")
    semester = context.user_data.get("semester", "Unknown")
    subject = context.user_data.get("subject", "Unknown")
    
    materials = STUDY_MATERIALS.get(branch, {}).get(semester, {}).get(subject, {}).get("materials", [])
    
    if not materials:
        text = f"❌ No materials available for {branch} Semester {semester} - {subject}."
        keyboard = [
            [
                InlineKeyboardButton("🔙 Back to Subjects", callback_data="back_to_subjects"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start"),
            ]
        ]
    else:
        text = f"📚 Available materials for {branch} Sem {semester} - {subject}:"
        keyboard = []
        
        for i, material in enumerate(materials):
            keyboard.append([InlineKeyboardButton(f"📄 {material['title']}", callback_data=f"material_{i}")])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Subjects", callback_data="back_to_subjects"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start"),
        ])
  
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data['current_state'] = MATERIAL_SELECTION
    return MATERIAL_SELECTION


# Ad Verification System
class AdVerificationSystem:
    def __init__(self):
        self.user_sessions = {}
        self.ad_clicks = {}
    
    def generate_verification_token(self, user_id, material_info):
        """Generate a unique verification token"""
        token = f"verify_{user_id}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Store session information
        self.user_sessions[token] = {
            'user_id': user_id,
            'material_info': material_info,
            'created_at': time.time(),
            'ad_clicked': False,
            'wait_start': None,
            'completed': False
        }
        
        return token
    
    def verify_ad_click(self, token):
        """Mark ad as clicked and start wait timer"""
        if token in self.user_sessions:
            self.user_sessions[token]['ad_clicked'] = True
            self.user_sessions[token]['wait_start'] = time.time()
            return True
        return False
    
    def check_verification_status(self, token):
        """Check if user can download file"""
        if token not in self.user_sessions:
            return False, "Invalid token"
        
        session = self.user_sessions[token]
        
        if not session['ad_clicked']:
            return False, "Ad not clicked"
        
        if session['completed']:
            return True, "Already verified"
        
        # Check if wait time has passed
        if session['wait_start']:
            elapsed = time.time() - session['wait_start']
            if elapsed >= config.WAIT_TIME_SECONDS:
                session['completed'] = True
                return True, "Verification complete"
            else:
                remaining = config.WAIT_TIME_SECONDS - int(elapsed)
                return False, f"Wait {remaining} more seconds"
        
        return False, "Verification in progress"
    
    def cleanup_old_sessions(self):
        """Clean up sessions older than 1 hour"""
        current_time = time.time()
        expired_tokens = []
        
        for token, session in self.user_sessions.items():
            if current_time - session['created_at'] > 3600:  # 1 hour
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.user_sessions[token]

# Initialize ad verification system
ad_verification = AdVerificationSystem()

# Fixed Smart Ad System with 10-hour free download reset
class SmartAdSystem:
    def __init__(self):
        self.user_sessions = {}
        self.user_tokens = {}
        self.user_stats = {}
    
    def get_user_data(self, user_id):
        """Get or create user data with proper 10-hour reset"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                'free_downloads_used': 0,
                'total_downloads': 0,
                'tokens_earned': 0,
                'last_ad_watch': None,
                'free_downloads_reset_time': time.time() + (config.FREE_DOWNLOAD_RESET_HOURS * 3600),
                'last_reset': time.time()
            }
        return self.user_stats[user_id]
    
    def reset_free_downloads_if_needed(self, user_id):
        """Reset free downloads if 10 hours have passed - FIXED LOGIC"""
        user_data = self.get_user_data(user_id)
        current_time = time.time()
        
        # Check if reset time has passed
        if current_time >= user_data['free_downloads_reset_time']:
            # Reset free downloads and set new reset time (10 hours from now)
            user_data['free_downloads_used'] = 0
            user_data['free_downloads_reset_time'] = current_time + (config.FREE_DOWNLOAD_RESET_HOURS * 3600)
            user_data['last_reset'] = current_time
            logger.info(f"Reset free downloads for user {user_id}")
            return True
        return False
    
    def can_download_free(self, user_id):
        """Check if user can download for free (resets every 10 hours) - FIXED"""
        user_data = self.get_user_data(user_id)
        
        # Always check if we need to reset free downloads
        self.reset_free_downloads_if_needed(user_id)
        
        # User can download free if they haven't used all free downloads
        return user_data['free_downloads_used'] < config.FREE_DOWNLOADS_ALLOWED
    
    def has_valid_token(self, user_id):
        """Check if user has valid token"""
        if user_id in self.user_tokens:
            token_data = self.user_tokens[user_id]
            if time.time() < token_data['expires_at']:
                return True
            else:
                # Token expired, remove it
                del self.user_tokens[user_id]
                logger.info(f"Token expired for user {user_id}")
        return False
    
    def use_free_download(self, user_id):
        """Use one free download and return new count"""
        user_data = self.get_user_data(user_id)
        
        # Make sure we're not exceeding free downloads
        if user_data['free_downloads_used'] < config.FREE_DOWNLOADS_ALLOWED:
            user_data['free_downloads_used'] += 1
            user_data['total_downloads'] += 1
            logger.info(f"Free download used by {user_id}. Now {user_data['free_downloads_used']}/{config.FREE_DOWNLOADS_ALLOWED}")
            return user_data['free_downloads_used']
        else:
            logger.warning(f"User {user_id} tried to use free download but none left")
            return user_data['free_downloads_used']
    
    def grant_token(self, user_id):
        """Grant 10-hour token to user"""
        current_time = time.time()
        self.user_tokens[user_id] = {
            'created_at': current_time,
            'expires_at': current_time + (config.TOKEN_DURATION_HOURS * 3600)
        }
        user_data = self.get_user_data(user_id)
        user_data['tokens_earned'] += 1
        user_data['last_ad_watch'] = current_time
        logger.info(f"Granted {config.TOKEN_DURATION_HOURS}-hour token to user {user_id}")
    
    def get_user_status(self, user_id):
        """Get user's download status with time remaining - FIXED"""
        user_data = self.get_user_data(user_id)
        
        # Check if free downloads need reset (IMPORTANT: Call this every time)
        self.reset_free_downloads_if_needed(user_id)
        
        free_remaining = config.FREE_DOWNLOADS_ALLOWED - user_data['free_downloads_used']
        has_token = self.has_valid_token(user_id)
        
        # Calculate time until free downloads reset
        current_time = time.time()
        reset_time_remaining = user_data['free_downloads_reset_time'] - current_time
        hours_until_reset = max(0, reset_time_remaining // 3600)
        minutes_until_reset = max(0, (reset_time_remaining % 3600) // 60)
        
        if has_token:
            token_expiry = self.user_tokens[user_id]['expires_at']
            token_time_remaining = token_expiry - current_time
            token_hours_left = max(0, token_time_remaining // 3600)
            token_minutes_left = max(0, (token_time_remaining % 3600) // 60)
            
            return {
                'status': 'token_active',
                'free_remaining': free_remaining,
                'free_total': config.FREE_DOWNLOADS_ALLOWED,
                'token_hours_left': token_hours_left,
                'token_minutes_left': token_minutes_left,
                'total_downloads': user_data['total_downloads'],
                'hours_until_reset': hours_until_reset,
                'minutes_until_reset': minutes_until_reset
            }
        elif free_remaining > 0:
            return {
                'status': 'free_downloads',
                'free_remaining': free_remaining,
                'free_total': config.FREE_DOWNLOADS_ALLOWED,
                'total_downloads': user_data['total_downloads'],
                'hours_until_reset': hours_until_reset,
                'minutes_until_reset': minutes_until_reset
            }
        else:
            return {
                'status': 'needs_ad',
                'free_remaining': 0,
                'free_total': config.FREE_DOWNLOADS_ALLOWED,
                'total_downloads': user_data['total_downloads'],
                'hours_until_reset': hours_until_reset,
                'minutes_until_reset': minutes_until_reset
            }
    
    def generate_verification_token(self, user_id, material_info):
        """Generate verification token for ad watching"""
        token = f"verify_{user_id}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        self.user_sessions[token] = {
            'user_id': user_id,
            'material_info': material_info,
            'created_at': time.time(),
            'ad_clicked': False,
            'wait_start': None,
            'completed': False
        }
        
        return token
    
    def verify_ad_click(self, token):
        """Mark ad as clicked and start wait timer"""
        if token in self.user_sessions:
            self.user_sessions[token]['ad_clicked'] = True
            self.user_sessions[token]['wait_start'] = time.time()
            logger.info(f"Ad clicked for token {token}")
            return True
        return False
    
    def check_verification_status(self, token):
        """Check if user can download file"""
        if token not in self.user_sessions:
            return False, "Invalid token"
        
        session = self.user_sessions[token]
        
        if not session['ad_clicked']:
            return False, "Please click the ad link first"
        
        if session['completed']:
            return True, "Already verified"
        
        # Check if wait time has passed
        if session['wait_start']:
            elapsed = time.time() - session['wait_start']
            if elapsed >= config.WAIT_TIME_SECONDS:
                session['completed'] = True
                
                # Grant token to user
                self.grant_token(session['user_id'])
                
                return True, f"Verification complete! 🎉 You now have {config.TOKEN_DURATION_HOURS} hours of unlimited downloads!"
            else:
                remaining = config.WAIT_TIME_SECONDS - int(elapsed)
                return False, f"Please wait {remaining} more seconds with the ad page open"
        
        return False, "Verification in progress"
    
    def cleanup_old_sessions(self):
        """Clean up old sessions"""
        current_time = time.time()
        expired_tokens = []
        
        for token, session in self.user_sessions.items():
            if current_time - session['created_at'] > 3600:  # 1 hour
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.user_sessions[token]

# Initialize smart ad system
smart_ad_system = SmartAdSystem()

# Save/Load user stats to file
# Fixed Smart Ad System initialization
def load_user_stats():
    """Load user statistics from file with error handling"""
    try:
        with open('user_stats.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convert string keys back to integers for user_id
            stats = {}
            for k, v in data.items():
                try:
                    stats[int(k)] = v
                except (ValueError, TypeError):
                    stats[k] = v
            return stats
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.info(f"Creating new user stats file: {e}")
        return {}

def save_user_stats():
    """Save user statistics to file with error handling"""
    try:
        with open('user_stats.json', 'w', encoding='utf-8') as f:
            # Convert user_id to string for JSON
            data = {str(k): v for k, v in smart_ad_system.user_stats.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("User stats saved successfully")
    except Exception as e:
        logger.error(f"Error saving user stats: {e}")

# Load user stats at startup
smart_ad_system.user_stats = load_user_stats()
logger.info(f"Loaded user stats for {len(smart_ad_system.user_stats)} users")


async def debug_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to check user status"""
    user_id = update.effective_user.id
    user_status = smart_ad_system.get_user_status(user_id)
    
    debug_text = f"""
🔧 **Debug Information - User {user_id}**

**Current Status:**
- Free Downloads Used: {user_status['free_remaining']}/{user_status['free_total']}
- Status: {user_status['status']}
- Total Downloads: {user_status['total_downloads']}
- Reset In: {user_status['hours_until_reset']}h {user_status['minutes_until_reset']}m

**System State:**
- AD_VERIFICATION_ENABLED: {config.AD_VERIFICATION_ENABLED}
- FREE_DOWNLOADS_ALLOWED: {config.FREE_DOWNLOADS_ALLOWED}
- TOKEN_DURATION_HOURS: {config.TOKEN_DURATION_HOURS}
"""
    
    await update.message.reply_text(debug_text, parse_mode="Markdown")

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset user's download count (for testing)"""
    user_id = update.effective_user.id
    if user_id in smart_ad_system.user_stats:
        smart_ad_system.user_stats[user_id]['free_downloads_used'] = 0
        smart_ad_system.user_stats[user_id]['free_downloads_reset_time'] = time.time() + (10 * 3600)
        save_user_stats()
        await update.message.reply_text("✅ User stats reset for testing")
    else:
        await update.message.reply_text("❌ User not found in stats")


# Ad tracking functions
def load_ad_stats():
    """Load advertisement statistics"""
    try:
        with open('ad_stats.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "total_impressions": 0,
            "ad_clicks": {},
            "conversions": 0,
            "revenue_earned": 0.0
        }

def save_ad_stats(stats):
    """Save advertisement statistics"""
    try:
        with open('ad_stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving ad stats: {e}")

def record_ad_conversion(user_id, ad_id, amount=0.02):
    """Record successful ad conversion"""
    stats = load_ad_stats()
    
    stats['conversions'] = stats.get('conversions', 0) + 1
    stats['revenue_earned'] = stats.get('revenue_earned', 0.0) + amount
    
    if ad_id not in stats['ad_clicks']:
        stats['ad_clicks'][ad_id] = {'clicks': 0, 'conversions': 0}
    
    stats['ad_clicks'][ad_id]['conversions'] = stats['ad_clicks'][ad_id].get('conversions', 0) + 1
    
    save_ad_stats(stats)
    logger.info(f"Ad conversion recorded: user {user_id}, ad {ad_id}")

async def show_ad_verification(update: Update, context: ContextTypes.DEFAULT_TYPE, material_index: int):
    """Show ad verification required before download"""
    query = update.callback_query
    await query.answer()
    
    branch = context.user_data.get("branch")
    semester = context.user_data.get("semester")
    subject = context.user_data.get("subject")
    
    materials = STUDY_MATERIALS.get(branch, {}).get(semester, {}).get(subject, {}).get("materials", [])
    
    if material_index >= len(materials):
        await query.edit_message_text("❌ Material not found.")
        return await start(update, context)
    
    material = materials[material_index]
    
    # Get random ad
    ad = random.choice(config.ADS)
    user_id = update.effective_user.id
    
    # Generate verification token
    material_info = {
        'branch': branch,
        'semester': semester,
        'subject': subject,
        'material_index': material_index,
        'material_title': material['title']
    }
    
    verification_token = ad_verification.generate_verification_token(user_id, material_info)
    
    # Create tracking URL with user ID and token
    tracking_url = ad['tracking_url'].format(user_id=user_id)
    final_url = f"{tracking_url}&token={verification_token}"
    
    # Store ad info in context for later verification
    context.user_data['current_verification'] = {
        'token': verification_token,
        'ad_id': ad['ad_id'],
        'material_index': material_index
    }
    
    text = (
        f"📢 **Ad Verification Required**\n\n"
        f"To download **{material['title']}**, please:\n\n"
        f"1. 🔗 **Click the ad link below**\n"
        f"2. ⏳ **Wait for {config.WAIT_TIME_SECONDS} seconds**\n"
        f"3. ✅ **Return here and click 'Verify & Download'**\n\n"
        f"**Ad Sponsor:** {ad['text']}\n\n"
        f"This helps us keep the bot free for everyone! 🙏"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔗 Click Ad Link (Required)", url=final_url)],
        [InlineKeyboardButton("✅ Verify & Download", callback_data=f"verify_download_{verification_token}")],
        [InlineKeyboardButton("🔄 Check Status", callback_data=f"check_status_{verification_token}")],
        [InlineKeyboardButton("❌ Cancel Download", callback_data="back_to_subjects")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    # Track ad impression
    stats = load_ad_stats()
    stats['total_impressions'] += 1
    if ad['ad_id'] not in stats['ad_clicks']:
        stats['ad_clicks'][ad['ad_id']] = {'clicks': 0, 'conversions': 0}
    save_ad_stats(stats)

async def handle_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verification button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("verify_download_"):
        token = data.replace("verify_download_", "")
        await process_download_verification(update, context, token)
    
    elif data.startswith("check_status_"):
        token = data.replace("check_status_", "")
        await check_verification_status(update, context, token)
    
    elif data == "show_my_status":
        await show_user_status(update, context)

async def process_download_verification(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str):
    """Process download after ad verification"""
    query = update.callback_query
    
    # Check verification status
    is_verified, message = smart_ad_system.check_verification_status(token)
    
    if not is_verified:
        # Show wait message with countdown
        if "wait" in message.lower():
            remaining = int(message.split(" ")[2])  # Extract seconds from message
            text = (
                f"⏳ **Please Wait**\n\n"
                f"{message}\n\n"
                f"🔗 **Keep the ad page open!**\n"
                f"⏰ **Time remaining:** {remaining} seconds\n\n"
                f"🎉 After this, you'll get {config.TOKEN_DURATION_HOURS} hours of unlimited downloads!"
            )
        else:
            text = f"❌ **Action Required**\n\n{message}\n\nPlease click the ad link first!"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Check Again", callback_data=f"verify_download_{token}")],
            [InlineKeyboardButton("📊 My Status", callback_data="show_my_status")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_to_subjects")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return
    
    # Verification successful - send the file
    session = smart_ad_system.user_sessions[token]
    material_info = session['material_info']
    
    branch = material_info['branch']
    semester = material_info['semester']
    subject = material_info['subject']
    material_index = material_info['material_index']
    
    materials = STUDY_MATERIALS.get(branch, {}).get(semester, {}).get(subject, {}).get("materials", [])
    material = materials[material_index]
    file_id = material.get("file_id")
    
    if not file_id:
        await query.edit_message_text("❌ File not available. Please contact admin.")
        return
    
    # Record successful conversion
    ad_id = context.user_data.get('current_verification', {}).get('ad_id', 'unknown')
    record_ad_conversion(update.effective_user.id, ad_id)
    
    # Send the file
    try:
        user_status = smart_ad_system.get_user_status(update.effective_user.id)
        
        caption = (
            f"✅ **Download Ready!**\n\n"
            f"📚 {material['title']}\n"
            f"🏛️ Branch: {branch}\n"
            f"📅 Semester: {semester}\n"
            f"📖 Subject: {subject}\n\n"
        )
        
        if user_status['status'] == 'token_active':
            caption += f"🎉 **{config.TOKEN_DURATION_HOURS}-Hour Token Active!**\nUnlimited downloads for {user_status['token_hours_left']} hours!"
        
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file_id,
            caption=caption,
            filename=f"{material['title']}.pdf"
        )
        
        # Success message
        if "token granted" in message:
            text = f"🎉 **Success!**\n\n{message}\n\n**{material['title']}** has been sent!\n\nEnjoy unlimited downloads for {config.TOKEN_DURATION_HOURS} hours! 🚀"
        else:
            text = f"✅ **Download Complete!**\n\n**{material['title']}** has been sent!"
        
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        text = f"❌ Error sending file. Please try again or contact admin."
    
    keyboard = [
        [InlineKeyboardButton("📚 More Materials", callback_data="back_to_subjects")],
        [InlineKeyboardButton("📊 My Status", callback_data="show_my_status")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    # Clean up verification data
    if token in smart_ad_system.user_sessions:
        del smart_ad_system.user_sessions[token]
    if 'current_verification' in context.user_data:
        del context.user_data['current_verification']
    
    # Save user stats
    save_user_stats()

async def check_verification_status(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str):
    """Check and display verification status"""
    query = update.callback_query
    await query.answer()
    
    is_verified, message = ad_verification.check_verification_status(token)
    
    if is_verified:
        text = f"✅ **Verification Complete!**\n\nYou can now download the file."
        keyboard = [[InlineKeyboardButton("📥 Download Now", callback_data=f"verify_download_{token}")]]
    else:
        session = ad_verification.user_sessions.get(token, {})
        material_title = session.get('material_info', {}).get('material_title', 'the file')
        
        if session.get('ad_clicked'):
            if "Wait" in message:
                remaining = int(message.split(" ")[1])
                text = (
                    f"⏳ **Verification in Progress**\n\n"
                    f"Ad clicked ✅\n"
                    f"Waiting time: {remaining} seconds remaining\n\n"
                    f"Please wait patiently..."
                )
            else:
                text = f"❌ **Verification Issue**\n\n{message}"
        else:
            text = (
                f"📢 **Action Required**\n\n"
                f"To download **{material_title}**, you need to:\n\n"
                f"1. 🔗 **Click the ad link**\n"
                f"2. ⏳ **Wait {config.WAIT_TIME_SECONDS} seconds**\n"
                f"3. ✅ **Click 'Verify & Download'**\n\n"
                f"Please click the ad link first!"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔗 Click Ad Link", url="#")],  # URL would be stored in context
            [InlineKeyboardButton("✅ Verify & Download", callback_data=f"verify_download_{token}")],
            [InlineKeyboardButton("🔄 Check Status", callback_data=f"check_status_{token}")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Modified material selection to use ad verification
async def select_material(update: Update, context: ContextTypes.DEFAULT_TYPE, material_index: int):
    """Fixed material selection with comprehensive error handling"""
    try:
        logger.info(f"select_material called with index: {material_index}")
        
        if not config.AD_VERIFICATION_ENABLED:
            logger.info("Ad system disabled, sending direct")
            return await send_material_direct(update, context, material_index)
        
        user_id = update.effective_user.id
        logger.info(f"Processing download for user: {user_id}")
        
        user_status = smart_ad_system.get_user_status(user_id)
        logger.info(f"User status: {user_status}")
        
        if user_status['status'] == 'free_downloads':
            logger.info("User has free downloads available")
            # Free download available - use it
            free_used = smart_ad_system.use_free_download(user_id)
            save_user_stats()
            
            query = update.callback_query
            await query.answer()
            
            remaining_free = config.FREE_DOWNLOADS_ALLOWED - free_used
            reset_time = f"{int(user_status['hours_until_reset'])}h {int(user_status['minutes_until_reset'])}m"
            
            text = (
                f"🎉 **Free Download Used!**\n\n"
                f"You have **{remaining_free} free downloads** remaining.\n"
                f"Free downloads reset in: **{reset_time}**\n\n"
                f"After free downloads, watch one ad to get {config.TOKEN_DURATION_HOURS} hours of unlimited downloads!"
            )
            
            # Determine if this is from search or browse
            is_search = 'search_results' in context.user_data
            
            if is_search:
                callback_data = f"free_download_search_{material_index}"
                logger.info(f"Search free download, callback: {callback_data}")
            else:
                callback_data = f"free_download_{material_index}"
                logger.info(f"Browse free download, callback: {callback_data}")
                
            keyboard = [[InlineKeyboardButton("✅ Download Now", callback_data=callback_data)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            return
            
        elif user_status['status'] == 'token_active':
            logger.info("User has active token, downloading directly")
            return await send_material_direct(update, context, material_index)
        
        else:
            logger.info("User needs ad verification")
            return await show_ad_verification(update, context, material_index)
            
    except Exception as e:
        logger.error(f"Error in select_material: {str(e)}")
        logger.error(traceback.format_exc())
        
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ Error in download process. Please try again.")
        return await start(update, context)

async def handle_free_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fixed free download handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        logger.info(f"handle_free_download called with: {data}")
        
        if data.startswith("free_download_search_"):
            # Search path
            material_index = int(data.replace("free_download_search_", ""))
            logger.info(f"Processing search free download index: {material_index}")
            
            results = context.user_data.get("search_results", [])
            if material_index < len(results):
                result = results[material_index]
                # Update context with search result data
                context.user_data["branch"] = result["branch"]
                context.user_data["semester"] = result["semester"]
                context.user_data["subject"] = result["subject"]
                
                # Find actual material index in database
                materials = STUDY_MATERIALS.get(result["branch"], {}).get(result["semester"], {}).get(result["subject"], {}).get("materials", [])
                actual_index = -1
                for idx, mat in enumerate(materials):
                    if mat.get("title") == result["material"].get("title"):
                        actual_index = idx
                        break
                
                logger.info(f"Actual material index: {actual_index}")
                
                if actual_index != -1:
                    await send_material_direct(update, context, actual_index)
                else:
                    await query.edit_message_text("❌ Material not found in database.")
            else:
                await query.edit_message_text("❌ Search result not found.")
                
        else:
            # Browse path
            material_index = int(data.replace("free_download_", ""))
            logger.info(f"Processing browse free download index: {material_index}")
            await send_material_direct(update, context, material_index)
            
    except Exception as e:
        logger.error(f"Error in handle_free_download: {str(e)}")
        logger.error(traceback.format_exc())
        
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ Error processing free download. Please try again.")
        return await start(update, context)

async def show_ad_verification(update: Update, context: ContextTypes.DEFAULT_TYPE, material_index: int):
    """Show ad verification for both browse and search paths"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_status = smart_ad_system.get_user_status(user_id)
    
    # Get material info based on context (browse or search)
    material_title = ""
    is_search = 'search_results' in context.user_data
    
    if is_search:
        # Search path
        results = context.user_data.get("search_results", [])
        if material_index < len(results):
            result = results[material_index]
            branch = result["branch"]
            semester = result["semester"]
            subject = result["subject"]
            material = result["material"]
            material_title = material["title"]
            
            # Store in context for the verification process
            context.user_data["branch"] = branch
            context.user_data["semester"] = semester
            context.user_data["subject"] = subject
        else:
            await query.edit_message_text("❌ Search result not found.")
            return await start(update, context)
    else:
        # Browse path
        branch = context.user_data.get("branch")
        semester = context.user_data.get("semester")
        subject = context.user_data.get("subject")
        
        materials = STUDY_MATERIALS.get(branch, {}).get(semester, {}).get(subject, {}).get("materials", [])
        if material_index >= len(materials):
            await query.edit_message_text("❌ Material not found.")
            return await start(update, context)
        
        material = materials[material_index]
        material_title = material["title"]
    
    # Get random ad
    ad = random.choice(config.ADS)
    
    # Generate verification token
    material_info = {
        'branch': context.user_data.get("branch"),
        'semester': context.user_data.get("semester"),
        'subject': context.user_data.get("subject"),
        'material_index': material_index,
        'material_title': material_title,
        'is_search': is_search
    }
    
    verification_token = smart_ad_system.generate_verification_token(user_id, material_info)
    
    # Create tracking URL
    tracking_url = ad['tracking_url'].format(user_id=user_id, token=verification_token)
    
    # Store ad info in context
    context.user_data['current_verification'] = {
        'token': verification_token,
        'ad_id': ad['ad_id'],
        'material_index': material_index,
        'is_search': is_search
    }
    
    # Create status message
    status_text = (
        f"📊 **Your Download Status**\n"
        f"• Free downloads used: {user_status['free_remaining']}/{config.FREE_DOWNLOADS_ALLOWED}\n"
        f"• Free downloads reset in: {int(user_status['hours_until_reset'])}h {int(user_status['minutes_until_reset'])}m\n\n"
    )
    
    text = (
        f"{status_text}"
        f"📢 **Ad Verification Required**\n\n"
        f"To download **{material_title}**, please:\n\n"
        f"1. 🔗 **Click the ad link below**\n"
        f"2. ⏳ **Keep it open for {config.WAIT_TIME_SECONDS} seconds**\n"
        f"3. ✅ **Return and click 'Verify & Download'**\n"
        f"4. 🎉 **Get {config.TOKEN_DURATION_HOURS}-hour unlimited downloads!**\n\n"
        f"**Ad Sponsor:** {ad['text']}\n\n"
        f"This helps us keep the bot free! 🙏"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔗 Click Ad Link (Required)", url=tracking_url)],
        [InlineKeyboardButton("✅ Verify & Download", callback_data=f"verify_download_{verification_token}")],
        [InlineKeyboardButton("🔄 Check Status", callback_data=f"check_status_{verification_token}")],
        [InlineKeyboardButton("📊 My Status", callback_data="show_my_status")],
    ]
    
    # Add appropriate cancel button based on context
    if is_search:
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_to_search")])
    else:
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_to_subjects")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    # Track ad impression
    stats = load_ad_stats()
    stats['total_impressions'] += 1
    if ad['ad_id'] not in stats['ad_clicks']:
        stats['ad_clicks'][ad['ad_id']] = {'clicks': 0, 'conversions': 0}
    save_ad_stats(stats)

async def show_user_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's download status with accurate 10-hour reset info"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_status = smart_ad_system.get_user_status(user_id)
    
    # Force refresh the status to ensure latest reset time
    user_status = smart_ad_system.get_user_status(user_id)
    
    if user_status['status'] == 'free_downloads':
        reset_time = f"{int(user_status['hours_until_reset'])}h {int(user_status['minutes_until_reset'])}m"
        text = (
            f"📊 **Your Download Status**\n\n"
            f"🎉 **Free Downloads Available!**\n"
            f"• Free downloads left: **{user_status['free_remaining']}/{config.FREE_DOWNLOADS_ALLOWED}**\n"
            f"• Free downloads reset in: **{reset_time}**\n"
            f"• Total downloads: {user_status['total_downloads']}\n\n"
            f"💡 After {config.FREE_DOWNLOADS_ALLOWED} free downloads, watch one ad for {config.WAIT_TIME_SECONDS} seconds to get {config.TOKEN_DURATION_HOURS} hours of unlimited downloads!"
        )
    elif user_status['status'] == 'token_active':
        token_time = f"{int(user_status['token_hours_left'])}h {int(user_status['token_minutes_left'])}m"
        reset_time = f"{int(user_status['hours_until_reset'])}h {int(user_status['minutes_until_reset'])}m"
        text = (
            f"📊 **Your Download Status**\n\n"
            f"✅ **Token Active!**\n"
            f"• Free downloads used: {user_status['free_remaining']}/{config.FREE_DOWNLOADS_ALLOWED}\n"
            f"• Token expires in: **{token_time}**\n"
            f"• Free downloads reset in: {reset_time}\n"
            f"• Total downloads: {user_status['total_downloads']}\n\n"
            f"🎉 You can download **unlimited materials** until token expires!"
        )
    else:
        reset_time = f"{int(user_status['hours_until_reset'])}h {int(user_status['minutes_until_reset'])}m"
        text = (
            f"📊 **Your Download Status**\n\n"
            f"📢 **Ad Watch Required**\n"
            f"• Free downloads used: {config.FREE_DOWNLOADS_ALLOWED}/{config.FREE_DOWNLOADS_ALLOWED}\n"
            f"• Free downloads reset in: **{reset_time}**\n"
            f"• Total downloads: {user_status['total_downloads']}\n\n"
            f"💡 Watch one ad for **{config.WAIT_TIME_SECONDS} seconds** to get **{config.TOKEN_DURATION_HOURS} hours** of unlimited downloads!"
        )
    
    keyboard = [
        [InlineKeyboardButton("📚 Continue Browsing", callback_data="back_to_subjects")],
        [InlineKeyboardButton("🔍 Search Materials", callback_data="search")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def send_material_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, material_index: int):
    """Fixed direct material sending with error handling"""
    try:
        query = update.callback_query
        await query.answer()
        
        logger.info(f"send_material_direct called with index: {material_index}")
        
        # Determine if this is from search or browse
        is_search = 'search_results' in context.user_data
        
        branch = context.user_data.get("branch")
        semester = context.user_data.get("semester") 
        subject = context.user_data.get("subject")
        
        logger.info(f"Context - Branch: {branch}, Semester: {semester}, Subject: {subject}, Is Search: {is_search}")
        
        if is_search:
            # Search path
            results = context.user_data.get("search_results", [])
            logger.info(f"Search results count: {len(results)}")
            
            if material_index < len(results):
                result = results[material_index]
                material = result["material"]
                file_id = material.get("file_id")
                material_title = material.get("title")
                
                # Update context with search result data
                context.user_data["branch"] = result["branch"]
                context.user_data["semester"] = result["semester"]
                context.user_data["subject"] = result["subject"]
            else:
                await query.edit_message_text("❌ Search result not found.")
                return
        else:
            # Browse path
            materials = STUDY_MATERIALS.get(branch, {}).get(semester, {}).get(subject, {}).get("materials", [])
            logger.info(f"Browse materials count: {len(materials)}")
            
            if material_index < len(materials):
                material = materials[material_index]
                file_id = material.get("file_id")
                material_title = material.get("title")
            else:
                await query.edit_message_text("❌ Material not found.")
                return
        
        logger.info(f"Material title: {material_title}, File ID: {file_id}")
        
        if not file_id:
            text = f"❌ File not available for: {material_title}\n\nPlease contact admin."
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_subjects")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        
        # Send the file
        caption = f"📚 {material_title}\n\nEnjoy your study material! 📖"
        
        logger.info("Attempting to send document...")
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file_id,
            caption=caption,
            filename=f"{material_title}.pdf"
        )
        logger.info("Document sent successfully")
        
        text = f"✅ **{material_title}** has been sent!"
        
    except Exception as e:
        logger.error(f"Error in send_material_direct: {str(e)}")
        logger.error(traceback.format_exc())
        text = f"❌ Error sending file: {str(e)}"
    
    # Create appropriate navigation
    keyboard = []
    if is_search:
        keyboard.append([InlineKeyboardButton("🔙 Back to Results", callback_data="back_to_search")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 Back to Materials", callback_data="back_to_subjects")])
    
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# Donation system
async def show_donation_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show donation options to user"""
    text = (
        "❤️ **Support Our Study Material Bot**\n\n"
        "If this bot has helped you in your studies, consider supporting us to keep it running and add more features!\n\n"
        "**What your donation supports:**\n"
        "• 🤖 Server costs and maintenance\n"
        "• 📚 Adding new study materials\n"
        "• 🔧 Improving bot features\n"
        "• 🆓 Keeping content free for everyone\n\n"
        "💳 **Donation Options:**\n"
        f"• **UPI:** `{config.DONATION_OPTIONS['upi']}`\n"
    
        "Thank you for your support! 🙏"
    )
    
    keyboard = [
        [InlineKeyboardButton("💖 Copy UPI ID", callback_data="copy_upi")],
        [InlineKeyboardButton("📞 Contact Admin", url="https://t.me/your_admin_bot")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    return START

async def handle_donation_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle donation button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "copy_upi":
        # For UPI, we can't copy directly but we can show it prominently
        text = f"📋 **UPI ID for Donation:**\n\n`{config.DONATION_OPTIONS['upi']}`\n\nPlease copy this UPI ID and use any UPI app to send your donation. Thank you! ❤️"
        await query.edit_message_text(text, parse_mode="Markdown")
    
    
# Track donations
def log_donation(user_id, amount, method):
    """Log donation details"""
    donation_data = {
        "user_id": user_id,
        "amount": amount,
        "method": method,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        with open('donations.json', 'r') as f:
            donations = json.load(f)
    except:
        donations = []
    
    donations.append(donation_data)
    
    with open('donations.json', 'w') as f:
        json.dump(donations, f, indent=2)
    
    logger.info(f"Donation received: {amount} via {method} from user {user_id}")




async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show help information."""
    text = (
        "ℹ️ **Study Material Bot Help**\n\n"
        "This bot helps you find study materials for various engineering branches.\n\n"
        "**How to use:**\n"
        "• Use 'Browse by Branch' to navigate through branches, semesters, and subjects\n"
        "• Use 'Search' to find materials by keywords\n"
        "• Admins can upload new materials using the Upload button\n\n"
        "**Supported branches:** CSE, ECE, EEE, Mechanical, Civil\n"
        "**Semesters:** 1-8\n\n"
        "If you encounter any issues, please contact the administrator."
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    context.user_data['current_state'] = START
    return START

# Message handler for text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages based on current state."""
    current_state = context.user_data.get('current_state', START)
    
    if current_state == SEARCH_RESULTS:
        await handle_search(update, context)
    elif current_state == ADMIN_UPLOAD:
        await handle_admin_text(update, context)
    else:
        # Treat as search query
        context.user_data['current_state'] = SEARCH_RESULTS
        await handle_search(update, context)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and send a message to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Send a message to the user
    if update and update.effective_chat:
        text = "❌ Sorry, an error occurred. Please try again."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics"""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    # Load stats
    ad_stats = load_ad_stats()
    
    text = (
        "📊 **Bot Statistics**\n\n"
        f"📢 **Advertisement Performance:**\n"
        f"• Total Impressions: {ad_stats.get('total_impressions', 0)}\n"
        f"• Unique Users: {len(ad_stats.get('user_ad_count', {}))}\n\n"
        "💝 **Donation Tracking:**\n"
        "• Use /donations to see donation history\n\n"
        "⚙️ **Admin Commands:**\n"
        "• /stats - Show this statistics\n"
        "• /donations - Show donation history\n"
        "• /broadcast - Broadcast message to all users"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's download status via command"""
    user_id = update.effective_user.id
    user_status = smart_ad_system.get_user_status(user_id)
    
    if user_status['status'] == 'free_downloads':
        text = (
            f"📊 **Your Download Status**\n\n"
            f"🎉 **Free Downloads Available!**\n"
            f"• Free downloads left: {user_status['free_remaining']}/{config.FREE_DOWNLOADS_ALLOWED}\n"
            f"• Total downloads: {user_status['total_downloads']}\n\n"
            f"💡 After free downloads, watch one ad for {config.WAIT_TIME_SECONDS} seconds to get {config.TOKEN_DURATION_HOURS} hours of unlimited downloads!"
        )
    elif user_status['status'] == 'token_active':
        text = (
            f"📊 **Your Download Status**\n\n"
            f"✅ **Token Active!**\n"
            f"• Free downloads used: {user_status['free_remaining']}/{config.FREE_DOWNLOADS_ALLOWED}\n"
            f"• Total downloads: {user_status['total_downloads']}\n"
            f"• Token expires in: {user_status['token_hours_left']} hours\n\n"
            f"🎉 You can download unlimited materials until token expires!"
        )
    else:
        text = (
            f"📊 **Your Download Status**\n\n"
            f"📢 **Ad Watch Required**\n"
            f"• Free downloads used: {user_status['free_remaining']}/{config.FREE_DOWNLOADS_ALLOWED}\n"
            f"• Total downloads: {user_status['total_downloads']}\n\n"
            f"💡 Watch one ad for {config.WAIT_TIME_SECONDS} seconds to get {config.TOKEN_DURATION_HOURS} hours of unlimited downloads!"
        )
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def show_donations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show donation history"""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        with open('donations.json', 'r') as f:
            donations = json.load(f)
    except:
        donations = []
    
    if not donations:
        text = "📈 **Donation History**\n\nNo donations received yet."
    else:
        total = sum(d['amount'] for d in donations if 'amount' in d)
        text = f"📈 **Donation History**\n\nTotal Received: ₹{total}\n\nRecent Donations:\n"
        
        for i, donation in enumerate(donations[-5:]):  # Show last 5
            text += f"• ₹{donation.get('amount', 'N/A')} via {donation.get('method', 'Unknown')}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def check_github(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check GitHub connection"""
    from github_storage import github_storage
    
    if not github_storage:
        await update.message.reply_text("❌ GitHub storage not initialized")
        return
    
    try:
        # Test load
        data = github_storage.load_data()
        await update.message.reply_text(f"✅ GitHub connection working\nBranches: {len(data)}")
    except Exception as e:
        await update.message.reply_text(f"❌ GitHub error: {str(e)}")

async def force_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force save current data to GitHub"""
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    global STUDY_MATERIALS
    save_materials(STUDY_MATERIALS)
    await update.message.reply_text("💾 Force save initiated!")

async def check_storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check storage status"""
    from github_storage import github_storage
    
    text = "💾 **Storage Status**\n\n"
    
    if github_storage:
        text += "✅ GitHub storage: **ENABLED**\n"
        text += f"📁 Repository: `{github_storage.repo}`\n"
    else:
        text += "❌ GitHub storage: **DISABLED**\n"
        text += "💾 Using local storage only\n"
    
    # Check local file
    try:
        if os.path.exists('study_materials.json'):
            with open('study_materials.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_materials = 0
                for branch, semesters in data.items():
                    for semester, subjects in semesters.items():
                        for subject, subject_data in subjects.items():
                            total_materials += len(subject_data.get("materials", []))
                text += f"📊 Local file: **{total_materials}** materials across **{len(data)}** branches\n"
        else:
            text += "📁 Local file: **NOT FOUND**\n"
    except Exception as e:
        text += f"❌ Local file error: {str(e)}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


#--------------------------------------------------------------------------------------------------------------

# Main function
def main() -> None:
    """Start the bot."""
    # Initialize GitHub storage
    init_github_storage()
    # Check if token is set
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your bot token in config.py")
        return
        
    # Start Flask in background thread
    Thread(target=run_flask, daemon=True).start()

    # Start background async ping
    loop = asyncio.get_event_loop()
    loop.create_task(ping_server())
    
    # Create the Application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Add handlers - ORDER MATTERS!
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", admin_stats))  # If you have this
    application.add_handler(CommandHandler("donations", show_donations))  # If you have this
    application.add_handler(CommandHandler("ad_stats", ad_stats))  # ADD THIS
    application.add_handler(CommandHandler("toggle_ads", toggle_ads))  # ADD THIS
    application.add_handler(CommandHandler("status", my_status))
    # Add these to your main() function:
    application.add_handler(CommandHandler("debug", debug_user))
    application.add_handler(CommandHandler("reset", reset_user))
    # Add to main():
    application.add_handler(CommandHandler("github_status", check_github))
    application.add_handler(CommandHandler("force_save", force_save))
    application.add_handler(CommandHandler("storage", check_storage))

    # Team member upload handlers
    application.add_handler(MessageHandler(
        filters.Document.ALL & filters.ChatType.PRIVATE, 
        handle_team_upload_file
    ), group=1)
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_team_upload_text
    ), group=1)
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_admin_file))
    application.add_error_handler(error_handler)

    # Start the Bot
    print("🤖 Bot is starting with Ad Verification system...")
    print("📍 Press Ctrl+C to stop the bot")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
