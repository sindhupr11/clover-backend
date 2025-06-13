import re
import sys
import requests
import os
import json

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def query_groq(prompt):
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
        
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        result = response.json()
        if "choices" not in result or not result["choices"]:
            raise ValueError("Invalid response format from Groq API")
            
        return result["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        raise Exception("Groq API request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Groq API request failed: {str(e)}")
    except (KeyError, json.JSONDecodeError) as e:
        raise Exception(f"Failed to parse Groq API response: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error in Groq API call: {str(e)}")

# Function to read transcript from file
def read_transcript(file_path):
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

# Function to query Groq API for speaker identification
def identify_speaker(text_segment, context, previous_speaker):
    try:
        prompt = f"""
        Given the meeting transcript segment and context, identify the speaker.
        Context: {context}
        Segment: {text_segment}
        Previous speaker: {previous_speaker}
        Return the speaker's name in 'FirstName LastName' format or 'Unknown' if unclear.
        Rules:
        - The Scrum Master often prompts others (e.g., 'OK, [name]', 'Hello, [name]', 'Next, [name]') or uses 'OK', 'Hello', 'Thank you'.
        - Updates with 'yesterday', 'today', or 'blocker' belong to the prompted speaker.
        - Short responses (e.g., 'yeah', 'sure') may belong to the previous speaker or Scrum Master if following a prompt.
        - Responses to questions (e.g., 'Do you know why?') are from the previously prompted speaker.
        - Identify names from context cues like prompts or explicit mentions in the transcript.
        """
        result = query_groq(prompt)
        if result == "Unknown":
            return previous_speaker  # Return previous speaker instead of Unknown
        return result
    except Exception as e:
        print(f"Error in identify_speaker: {str(e)}")
        return previous_speaker  # Return previous speaker on error

# Function to clean and split transcript into segments
def parse_transcript(text):
    # Normalize text
    text = re.sub(r'(\s*hello\s*)+', ' hello ', text.lower())
    text = re.sub(r'\bshit\b', 'anshid', text)
    text = re.sub(r'\bliedida\b', 'ladeeda', text)
    text = re.sub(r'\bsaina\b', 'sayana', text)
    # Split into segments based on punctuation and key phrases
    segments = []
    current_segment = ""
    for char in text + " ":
        current_segment += char
        if char in '.!?':
            segments.append(current_segment.strip())
            current_segment = ""
        elif current_segment.strip().endswith((' ok', ' okay', ' yeah', ' thank you', ' bye')):
            segments.append(current_segment.strip())
            current_segment = ""
    if current_segment.strip():
        segments.append(current_segment.strip())
    return [s.strip() for s in segments if s.strip()]

# Function to extract names from transcript
def extract_names(segments):
    names = set()
    name_pattern = r'\b(start from|ok,?|hello,?|next,?|you can start)\s+([a-z]+)'
    for segment in segments:
        match = re.search(name_pattern, segment)
        if match:
            name = match.group(2).capitalize()
            names.add(name)
    return names

# Function to summarize updates
def summarize_updates(updates):
    if not updates:
        return "none"
    words = updates.split()
    if len(words) <= 10:
        return updates
    return ' '.join(words[:10]) + "..."

# Main processing logic
def process_transcript(transcript):
    try:
        if not transcript or not isinstance(transcript, str):
            raise ValueError("Invalid transcript: empty or not a string")

        segments = parse_transcript(transcript)
        if not segments:
            raise ValueError("No valid segments found in transcript")

        names = extract_names(segments)
        if not names:
            raise ValueError("No speaker names found in transcript")

        context = "Scrum meeting with multiple team members providing updates."
        current_speaker = "Unknown"
        summaries = {}
        
        for name in names:
            summaries[name] = {"yesterday": [], "today": [], "blockers": [], "time": "0:00"}

        segment_index = 0
        while segment_index < len(segments):
            segment = segments[segment_index]
            try:
                # Check for Scrum Master prompts
                speaker_match = re.search(r'\b(start from|ok,?|hello,?|next,?|you can start)\s+([a-z]+)', segment)
                if speaker_match:
                    current_speaker = speaker_match.group(2).capitalize()
                    if current_speaker in names:
                        summaries[current_speaker]["time"] = f"{segment_index // 2}:{segment_index % 2:02d}"
                elif re.search(r'\b(yesterday|today|blocker|pr)\b', segment):
                    speaker = identify_speaker(segment, context, current_speaker)
                    if speaker != "Unknown" and speaker in names:
                        current_speaker = speaker
                    if "yesterday" in segment:
                        summaries[current_speaker]["yesterday"].append(segment)
                    elif "today" in segment:
                        summaries[current_speaker]["today"].append(segment)
                    elif "blocker" in segment:
                        summaries[current_speaker]["blockers"].append(segment)
                context += f"\n{current_speaker}: {segment}"
            except Exception as e:
                print(f"Error processing segment {segment_index}: {str(e)}")
                # Continue with next segment
            segment_index += 1

        # Format output
        output = []
        for name in sorted(summaries.keys()):
            yesterday = summarize_updates(" ".join(summaries[name]["yesterday"]))
            today = summarize_updates(" ".join(summaries[name]["today"]))
            blockers = summarize_updates(" ".join(summaries[name]["blockers"]))
            output.append(f"{name}\ntime: {summaries[name]['time']}\nyesterday: {yesterday}\ntoday: {today}\nblockers: {blockers}")
        
        if not output:
            raise ValueError("No valid summaries generated")
            
        return "\n\n".join(output)
    except Exception as e:
        raise Exception(f"Failed to process transcript: {str(e)}")

# Main execution
if __name__ == "__main__":
    input_file = "a.txt"
    transcript = read_transcript(input_file)
    result = process_transcript(transcript)
    
    # Save output to file
    with open('scrum_summary.txt', 'w') as f:
        f.write(result)
