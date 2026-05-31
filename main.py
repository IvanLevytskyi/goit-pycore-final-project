import pickle
import re
from collections import UserDict
from datetime import datetime, timedelta
from pathlib import Path

# --- Address Book Classes ---

class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class Name(Field):
    pass

class Phone(Field):
    def __init__(self, value):
        if not self.validate(value):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)

    @staticmethod
    def validate(value):
        return bool(re.fullmatch(r"\d{10}", value))

class Email(Field):
    def __init__(self, value):
        if not self.validate(value):
            raise ValueError("Invalid email format.")
        super().__init__(value)

    @staticmethod
    def validate(value):
        return bool(re.fullmatch(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", value))

class Birthday(Field):
    def __init__(self, value):
        try:
            self.value = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Birthday format must be DD.MM.YYYY")

    def __str__(self):
        return self.value.strftime("%d.%m.%Y")

class Address(Field):
    pass

class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.emails = []
        self.birthday = None
        self.address = None

    def add_phone(self, phone_number):
        self.phones.append(Phone(phone_number))

    def remove_phone(self, phone_number):
        phone_to_remove = self.find_phone(phone_number)
        if phone_to_remove:
            self.phones.remove(phone_to_remove)
            return True
        return False

    def edit_phone(self, old_number, new_number):
        phone_to_edit = self.find_phone(old_number)
        if phone_to_edit:
            # Validate the new number before applying changes
            if not Phone.validate(new_number):
                raise ValueError("Phone number must contain exactly 10 digits.")
            phone_to_edit.value = new_number
            return True
        return False

    def find_phone(self, phone_number):
        for phone in self.phones:
            if phone.value == phone_number:
                return phone
        return None

    def add_email(self, email_address):
        self.emails.append(Email(email_address))

    def add_birthday(self, birthday_str):
        self.birthday = Birthday(birthday_str)

    def add_address(self, address_str):
        self.address = Address(address_str)

    def __str__(self):
        phones_str = "; ".join(p.value for p in self.phones) if self.phones else "none"
        emails_str = "; ".join(e.value for e in self.emails) if self.emails else "none"
        bday_str = str(self.birthday) if self.birthday else "not specified"
        addr_str = self.address.value if self.address else "not specified"
        
        return (f"Contact: {self.name.value}\n"
                f"  Phones:   {phones_str}\n"
                f"  Emails:   {emails_str}\n"
                f"  Address:  {addr_str}\n"
                f"  Birthday: {bday_str}\n")

class AddressBook(UserDict):
    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def delete(self, name):
        if name in self.data:
            del self.data[name]
            return True
        return False

    def get_upcoming_birthdays(self, days=7):
        upcoming = []
        today = datetime.today().date()
        
        for record in self.data.values():
            if not record.birthday:
                continue
            
            bday = record.birthday.value
            bday_this_year = bday.replace(year=today.year)
            
            if bday_this_year < today:
                bday_this_year = bday_this_year.replace(year=today.year + 1)
                
            delta_days = (bday_this_year - today).days
            
            if 0 <= delta_days <= days:
                # Move congratulation date to Monday if it falls on a weekend
                congratulation_date = bday_this_year
                if congratulation_date.weekday() == 5:    # Saturday
                    congratulation_date += timedelta(days=2)
                elif congratulation_date.weekday() == 6:  # Sunday
                    congratulation_date += timedelta(days=1)
                    
                upcoming.append({
                    "name": record.name.value,
                    "congratulation_date": congratulation_date.strftime("%d.%m.%Y")
                })
        return upcoming


# --- Note Classes ---

class Note:
    def __init__(self, title, content):
        self.title = title
        self.content = content

    def __str__(self):
        return f"[{self.title}]: {self.content}"

class NoteBook(UserDict):
    def add_note(self, title, content):
        self.data[title] = Note(title, content)

    def delete_note(self, title):
        if title in self.data:
            del self.data[title]
            return True
        return False

    def search_notes(self, keyword):
        # Search keyword in titles or content
        results = []
        for note in self.data.values():
            if keyword.lower() in note.title.lower() or keyword.lower() in note.content.lower():
                results.append(note)
        return results


# --- Storage Functions ---

# Use Path.home() to save data inside the user directory (e.g., C:\Users\Username)
STORAGE_DIR = Path.home() / ".assistant_data"
CONTACTS_FILE = STORAGE_DIR / "address_book.pkl"
NOTES_FILE = STORAGE_DIR / "notes.pkl"

def save_data(book, notebook):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONTACTS_FILE, "wb") as f:
        pickle.dump(book, f)
    with open(NOTES_FILE, "wb") as f:
        pickle.dump(notebook, f)

def load_data():
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE, "rb") as f:
            book = pickle.load(f)
    else:
        book = AddressBook()

    if NOTES_FILE.exists():
        with open(NOTES_FILE, "rb") as f:
            notebook = pickle.load(f)
    else:
        notebook = NoteBook()

    return book, notebook


# --- Input Error Decorator ---

def input_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, IndexError) as e:
            return f"Error: {e}"
    return inner


# --- Command Handlers (CLI Functions) ---

@input_error
def add_contact(args, book):
    if len(args) < 1:
        return "Please provide a contact name."
    name = args[0]
    record = book.find(name)
    if not record:
        record = Record(name)
        book.add_record(record)
        return f"Contact '{name}' successfully created. You can now add details to it."
    return f"Contact with name '{name}' already exists."

@input_error
def add_phone_to_contact(args, book):
    name, phone = args
    record = book.find(name)
    if record:
        record.add_phone(phone)
        return f"Phone number {phone} added for {name}."
    return f"Contact {name} not found."

@input_error
def add_email_to_contact(args, book):
    name, email = args
    record = book.find(name)
    if record:
        record.add_email(email)
        return f"Email {email} added for {name}."
    return f"Contact {name} not found."

@input_error
def add_birthday_to_contact(args, book):
    name, bday = args
    record = book.find(name)
    if record:
        record.add_birthday(bday)
        return f"Birthday {bday} added for {name}."
    return f"Contact {name} not found."

@input_error
def add_address_to_contact(args, book):
    name = args[0]
    address_str = " ".join(args[1:])
    record = book.find(name)
    if record:
        record.add_address(address_str)
        return f"Address added for {name}."
    return f"Contact {name} not found."

@input_error
def edit_phone_in_contact(args, book):
    name, old_phone, new_phone = args
    record = book.find(name)
    if record:
        if record.edit_phone(old_phone, new_phone):
            return f"Phone number changed from {old_phone} to {new_phone}."
        return f"Old phone number {old_phone} not found."
    return f"Contact {name} not found."

@input_error
def delete_contact(args, book):
    name = args[0]
    if book.delete(name):
        return f"Contact {name} deleted."
    return f"Contact {name} not found."

@input_error
def search_contact(args, book):
    name = args[0]
    record = book.find(name)
    if record:
        return str(record)
    return f"Contact {name} not found."

def show_all_contacts(book):
    if not book.data:
        return "Address book is empty."
    return "\n".join(str(record) for record in book.data.values())

@input_error
def birthdays(args, book):
    days = int(args[0]) if args else 7
    upcoming = book.get_upcoming_birthdays(days)
    if not upcoming:
        return f"No birthdays found within the next {days} days."
    
    result = f"Birthdays within the next {days} days:\n"
    for user in upcoming:
        result += f"- {user['name']}: congratulate on {user['congratulation_date']}\n"
    return result

# --- Note Handlers ---

@input_error
def add_note(args, notebook):
    title = args[0]
    content = " ".join(args[1:])
    notebook.add_note(title, content)
    return f"Note '{title}' successfully added."

@input_error
def edit_note(args, notebook):
    title = args[0]
    new_content = " ".join(args[1:])
    if title in notebook.data:
        notebook.add_note(title, new_content)
        return f"Note '{title}' updated."
    return f"Note '{title}' not found."

@input_error
def delete_note(args, notebook):
    title = args[0]
    if notebook.delete_note(title):
        return f"Note '{title}' deleted."
    return f"Note '{title}' not found."

@input_error
def search_notes(args, notebook):
    keyword = args[0]
    results = notebook.search_notes(keyword)
    if not results:
        return f"No notes found matching keyword '{keyword}'."
    return "\n".join(str(note) for note in results)

def show_all_notes(notebook):
    if not notebook.data:
        return "Notes list is empty."
    return "\n".join(str(note) for note in notebook.data.values())


# --- Input Parser ---

def parse_input(user_input):
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, args


# --- Main Application Loop ---

def main():
    # Load saved data from user's hard drive
    book, notebook = load_data()
    print("Welcome to Personal Assistant!")
    print(f"Data synced at directory: {STORAGE_DIR}")

    while True:
        user_input = input("\nEnter a command: ")
        if not user_input.strip():
            continue
            
        command, args = parse_input(user_input)

        # Exit application
        if command in ["close", "exit"]:
            save_data(book, notebook)
            print("Data saved. Good bye!")
            break

        # Address Book Commands
        elif command == "add-contact":
            print(add_contact(args, book))
        elif command == "add-phone":
            print(add_phone_to_contact(args, book))
        elif command == "add-email":
            print(add_email_to_contact(args, book))
        elif command == "add-birthday":
            print(add_birthday_to_contact(args, book))
        elif command == "add-address":
            print(add_address_to_contact(args, book))
        elif command == "edit-phone":
            print(edit_phone_in_contact(args, book))
        elif command == "delete-contact":
            print(delete_contact(args, book))
        elif command == "search-contact":
            print(search_contact(args, book))
        elif command == "all-contacts":
            print(show_all_contacts(book))
        elif command == "birthdays":
            print(birthdays(args, book))

        # Notes Commands
        elif command == "add-note":
            print(add_note(args, notebook))
        elif command == "edit-note":
            print(edit_note(args, notebook))
        elif command == "delete-note":
            print(delete_note(args, notebook))
        elif command == "search-note":
            print(search_notes(args, notebook))
        elif command == "all-notes":
            print(show_all_notes(notebook))

        # Help Manual
        elif command == "help":
            print("""Available commands:
  --- Contacts ---
  add-contact [name]
  add-phone [name] [10 digits]
  add-email [name] [email]
  add-birthday [name] [DD.MM.YYYY]
  add-address [name] [address text]
  edit-phone [name] [old_phone] [new_phone]
  delete-contact [name]
  search-contact [name]
  all-contacts
  birthdays [number_of_days (optional)]

  --- Notes ---
  add-note [title] [note content]
  edit-note [title] [new content]
  delete-note [title]
  search-note [keyword_to_search]
  all-notes

  --- System ---
  exit, close (save and exit)""")
        else:
            print("Unknown command. Try running 'help'.")


if __name__ == "__main__":
    main()
