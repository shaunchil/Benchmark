import re
import json
import statistics

def parse_edge_answers_file(filename="edge_answers.txt"):
    """
    Parse the edge_answers.txt file and extract model data for the dashboard
    """
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by model sections
    model_sections = re.split(r'=== Model: (.+?) ===', content)[1:]  # Skip first empty element
    
    models_data = {}
    all_questions = {}
    
    # Process each model section
    for i in range(0, len(model_sections), 2):
        model_name = model_sections[i].strip()
        model_content = model_sections[i + 1]
        
        # Find all Q&A pairs for this model
        qa_pattern = r'Q(\d+): (.+?)\nA: (.+?)\nGC: (.+?)\nScore: ([\d.]+)'
        matches = re.findall(qa_pattern, model_content, re.DOTALL)
        
        model_scores = []
        model_questions = []
        
        for match in matches:
            question_id = int(match[0])
            question = match[1].strip()
            answer = match[2].strip()
            ground_truth = match[3].strip()
            score = float(match[4])
            
            model_scores.append(score)
            model_questions.append({
                'id': question_id,
                'question': question,
                'answer': answer,
                'ground_truth': ground_truth,
                'score': score
            })
            
            # Store unique questions
            if question_id not in all_questions:
                all_questions[question_id] = {
                    'question': question,
                    'ground_truth': ground_truth,
                    'examples': []
                }
            
            all_questions[question_id]['examples'].append({
                'model': model_name,
                'answer': answer,
                'score': score
            })
        
        if model_scores:  # Only add models that have data
            models_data[model_name] = {
                'average_score': statistics.mean(model_scores),
                'questions': model_questions,
                'total_questions': len(model_questions)
            }
    
    return models_data, all_questions

def generate_dashboard_data(models_data, all_questions):
    """
    Generate JavaScript data format for the dashboard
    """
    
    # Extract model names and scores
    model_names = list(models_data.keys())
    model_scores = [round(models_data[model]['average_score'] * 100, 1) for model in model_names]
    
    # Prepare examples for dashboard
    examples_list = []
    for q_id in sorted(all_questions.keys()):
        question_data = all_questions[q_id]
        
        # Take first few examples to avoid overwhelming the dashboard
        limited_examples = question_data['examples'][:5]  # Show max 5 models per question
        
        examples_list.append({
            'id': q_id,
            'question': question_data['question'],
            'ground_truth': question_data['ground_truth'],
            'examples': limited_examples
        })
    
    # Generate JavaScript code
    js_data = f"""
        // AUTO-GENERATED DATA FROM edge_answers.txt
        const modelData = {{
            labels: {json.dumps(model_names)},
            scores: {json.dumps(model_scores)}
        }};

        const realExamples = {json.dumps(examples_list, indent=8)};
        
        // Statistics
        const stats = {{
            totalModels: {len(model_names)},
            totalQuestions: {len(all_questions)},
            averageScore: {round(statistics.mean(model_scores), 1)},
            topModel: "{model_names[model_scores.index(max(model_scores))]}",
            scoreRange: "{min(model_scores):.1f}% - {max(model_scores):.1f}%"
        }};
    """
    
    return js_data

def create_dashboard_with_data(models_data, all_questions, output_file="benchmark_dashboard.html"):
    """
    Create the complete HTML dashboard with embedded data
    """
    
    js_data = generate_dashboard_data(models_data, all_questions)
    
    # Get dashboard template (you'll need to save the HTML from the previous artifact)
    dashboard_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Benchmark Results</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        /* [CSS STYLES FROM PREVIOUS ARTIFACT WOULD GO HERE] */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f8fafc;
            color: #1a202c;
            line-height: 1.5;
        }
        /* ... rest of CSS ... */
    </style>
</head>
<body>
    <!-- [HTML BODY FROM PREVIOUS ARTIFACT WOULD GO HERE] -->
    <script>
''' + js_data + '''
        
        // [REST OF JAVASCRIPT FROM PREVIOUS ARTIFACT WOULD GO HERE]
        function initChart() {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: modelData.labels,
                    datasets: [{
                        label: 'Similarity Score (%)',
                        data: modelData.scores,
                        backgroundColor: modelData.scores.map(score => {
                            if (score >= 85) return '#48bb78';
                            if (score >= 75) return '#ed8936'; 
                            return '#e53e3e';
                        }),
                        borderWidth: 0,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        },
                        x: {
                            ticks: {
                                maxRotation: 45
                            }
                        }
                    }
                }
            });
        }
        
        function displayExamples() {
            const container = document.getElementById('examplesContainer');
            let html = '';
            
            realExamples.forEach(example => {
                example.examples.forEach(ex => {
                    const scoreClass = ex.score * 100 >= 85 ? 'score-high' : 
                                     ex.score * 100 >= 75 ? 'score-medium' : 'score-low';
                    
                    html += `
                        <div class="example-card">
                            <div class="question">Q${example.id}: ${example.question}</div>
                            <div class="comparison-grid">
                                <div class="answer-box model-answer">
                                    <div class="answer-header">🤖 ${ex.model} Response</div>
                                    <div class="answer-text">${ex.answer.substring(0, 300)}${ex.answer.length > 300 ? '...' : ''}</div>
                                    <div class="score ${scoreClass}">Score: ${(ex.score * 100).toFixed(1)}%</div>
                                </div>
                                <div class="answer-box ground-truth">
                                    <div class="answer-header">✅ Ground Truth</div>
                                    <div class="answer-text">${example.ground_truth}</div>
                                </div>
                            </div>
                        </div>
                    `;
                });
            });
            
            container.innerHTML = html;
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            initChart();
            displayExamples();
            
            // Update stats
            document.querySelector('[data-stat="models"]').textContent = stats.totalModels;
            document.querySelector('[data-stat="questions"]').textContent = stats.totalQuestions;
            document.querySelector('[data-stat="average"]').textContent = stats.averageScore + '%';
            document.querySelector('[data-stat="top"]').textContent = stats.topModel.split(':')[0];
            document.querySelector('[data-stat="range"]').textContent = stats.scoreRange;
        });
    </script>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(dashboard_template)
    
    print(f"✅ Dashboard created: {output_file}")

def main():
    """
    Main function to parse data and create dashboard
    """
    print("🔍 Parsing edge_answers.txt...")
    
    try:
        models_data, all_questions = parse_edge_answers_file()
        
        print(f"✅ Found {len(models_data)} models with data")
        print(f"✅ Found {len(all_questions)} unique questions")
        
        # Show summary
        print("\n📊 Model Performance Summary:")
        for model, data in models_data.items():
            avg_score = data['average_score'] * 100
            print(f"  {model}: {avg_score:.1f}% ({data['total_questions']} questions)")
        
        # Generate JavaScript data file
        js_data = generate_dashboard_data(models_data, all_questions)
        with open("dashboard_data.js", "w", encoding="utf-8") as f:
            f.write(js_data)
        
        print(f"\n✅ Generated dashboard_data.js")
        print("\n🚀 Next steps:")
        print("1. Copy the JavaScript data from dashboard_data.js")
        print("2. Replace the sample data in your HTML dashboard")
        print("3. Open the HTML file in your browser")
        
        return js_data, models_data, all_questions
        
    except FileNotFoundError:
        print("❌ Error: edge_answers.txt not found!")
        print("Make sure the file is in the same directory as this script.")
        return None, None, None
    except Exception as e:
        print(f"❌ Error parsing file: {e}")
        return None, None, None

if __name__ == "__main__":
    main()
