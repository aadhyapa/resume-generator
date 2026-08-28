import os
import json
import sys
from dotenv import load_dotenv

# Set paths. This script lives in backend/scripts/; its output belongs in
# backend/agents/test_data/, alongside the fixtures it feeds.
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
output_dir = os.path.join(backend_dir, "agents", "test_data")
sys.path.append(backend_dir)

from agents.embedder import generate_embedding

def main():
    print("Generating resume JSON with embeddings...")
    
    # 10 realistic resume bullets targeted at Siemens / CAD / CS internships
    raw_bullets = [
        {
            "bullet_id": "b1",
            "experience_id": "exp1",
            "company": "Siemens Digital Industries Software",
            "title": "QA Automation Engineer Co-op",
            "text": "Automated regression testing of CAD components using C++ and Python, increasing test coverage by 25% and detecting 12 critical bugs."
        },
        {
            "bullet_id": "b2",
            "experience_id": "exp1",
            "company": "Siemens Digital Industries Software",
            "title": "QA Automation Engineer Co-op",
            "text": "Drafted comprehensive design specifications and API documentation for CAD software modules to guide future software development."
        },
        {
            "bullet_id": "b3",
            "experience_id": "exp1",
            "company": "Siemens Digital Industries Software",
            "title": "QA Automation Engineer Co-op",
            "text": "Analyzed automated test suites and debugged integration issues in mechatronic simulation files, reducing test runtime by 15%."
        },
        {
            "bullet_id": "b4",
            "experience_id": "exp2",
            "company": "University of Cincinnati",
            "title": "Undergraduate Research Assistant",
            "text": "Developed object-oriented simulation tools in C# to calculate structural forces on 3D computer-aided design assemblies."
        },
        {
            "bullet_id": "b5",
            "experience_id": "exp2",
            "company": "University of Cincinnati",
            "title": "Undergraduate Research Assistant",
            "text": "Wrote clean, robust, and maintainable C++ algorithms for real-time visualization of high-dimensional geometric datasets."
        },
        {
            "bullet_id": "b6",
            "experience_id": "exp3",
            "company": "Personal Projects",
            "title": "Independent Developer",
            "text": "Built a lightweight 3D CAD model viewer in Python and WebGL, supporting interactive rotation and sectioning of assemblies."
        },
        {
            "bullet_id": "b7",
            "experience_id": "exp3",
            "company": "Personal Projects",
            "title": "Independent Developer",
            "text": "Designed a mechatronics prototype with Arduino and Python controllers to automate sensor readings and navigation."
        },
        {
            "bullet_id": "b8",
            "experience_id": "exp3",
            "company": "Personal Projects",
            "title": "Independent Developer",
            "text": "Created a robust C++ command-line parsing library following strict OOP principles and writing complete unit test suites."
        },
        {
            "bullet_id": "b9",
            "experience_id": "exp4",
            "company": "UC Robotics Club",
            "title": "Team Captain",
            "text": "Led a team of 4 engineering students in designing and programming an autonomous robot, winning 1st place in the region."
        },
        {
            "bullet_id": "b10",
            "experience_id": "exp4",
            "company": "UC Robotics Club",
            "title": "Team Captain",
            "text": "Communicated complex system design and software architecture concepts clearly to judges and university department leaders."
        }
    ]

    # Generate embeddings for each bullet
    for bullet in raw_bullets:
        print(f"Embedding bullet {bullet['bullet_id']}...")
        embedding = generate_embedding(bullet["text"])
        if not embedding:
            raise ValueError(f"Failed to generate embedding for bullet {bullet['bullet_id']}")
        bullet["embedding"] = embedding

    # Save to resume.json
    output_path = os.path.join(output_dir, "resume.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(raw_bullets, f, indent=2)

    print(f"Successfully generated resume JSON at: {output_path}")

if __name__ == "__main__":
    main()
