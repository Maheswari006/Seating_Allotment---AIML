
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
import io
import csv
from csp_solver import solve_allocation

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-for-session'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///allocations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model
class AllocationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.Text, nullable=False)  # Store allocation as JSON string
    room_input = db.Column(db.Text, nullable=False) # Store original room input
    dept_input = db.Column(db.Text, nullable=False) # Store original dept input

# Create database tables
with app.app_context():
    db.create_all()

def maintain_history_limit():
    """Keep only the last 10 allocations."""
    count = AllocationHistory.query.count()
    if count > 10:
        oldest = AllocationHistory.query.order_by(AllocationHistory.timestamp.asc()).limit(count - 10).all()
        for record in oldest:
            db.session.delete(record)
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get rooms from form
            room_blocks = request.form.getlist('room_block[]')
            room_floors = request.form.getlist('room_floor[]')
            room_names = request.form.getlist('room_name[]')
            room_capacities = request.form.getlist('room_capacity[]')
            rooms_input = [
                {'block': b, 'floor': f, 'name': n, 'capacity': int(cap)} 
                for b, f, n, cap in zip(room_blocks, room_floors, room_names, room_capacities) 
                if n and cap
            ]

            # Get departments from form
            dept_names = request.form.getlist('dept_name[]')
            dept_sections = request.form.getlist('dept_section[]')
            dept_students = request.form.getlist('dept_students[]')
            depts_input = [{'name': name, 'section': sec, 'students': int(std)} for name, sec, std in zip(dept_names, dept_sections, dept_students) if name and sec and std]

            if not rooms_input or not depts_input:
                flash("Please provide at least one room and one department.", "warning")
                return redirect(url_for('index'))

            # Run allocation
            solution, error = solve_allocation(rooms_input, depts_input)

            if error:
                flash(error, "danger")
                return redirect(url_for('index'))

            # Calculate total students per room for the "TOTAL" column
            room_totals = {}
            for alloc in solution:
                room_name = alloc['room']
                room_totals[room_name] = room_totals.get(room_name, 0) + alloc['num_students']
            
            for alloc in solution:
                alloc['room_total'] = room_totals[alloc['room']]

            # Temporary store inputs and result for display/save
            return render_template('result.html', allocation=solution, rooms=rooms_input, depts=depts_input)

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('index'))

    # If it's a GET request, check for pre-filled data (e.g., from Edit)
    pre_rooms = request.args.get('rooms')
    pre_depts = request.args.get('depts')
    
    if pre_rooms:
        pre_rooms = json.loads(pre_rooms)
    if pre_depts:
        pre_depts = json.loads(pre_depts)

    return render_template('index.html', pre_rooms=pre_rooms, pre_depts=pre_depts)

@app.route('/edit/<int:id>')
def edit_allocation(id):
    alloc = AllocationHistory.query.get_or_404(id)
    # Redirect to index with room and dept data as JSON strings in query params
    return redirect(url_for('index', rooms=alloc.room_input, depts=alloc.dept_input))

@app.route('/download', methods=['POST'])
def download_allocation():
    try:
        allocation_data = json.loads(request.form.get('allocation_data'))
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['BLOCK', 'FLOOR', 'ROOM NO', 'DEPT', 'SEC', 'ROLL NO', 'No. Students', 'TOTAL'])
        
        # Write data
        for row in allocation_data:
            writer.writerow([
                row.get('block', '-'),
                row.get('floor', '-'),
                row.get('room', '-'),
                row.get('dept', '-'),
                row.get('sec', '-'),
                row.get('roll_no_range', '-'),
                row.get('num_students', '-'),
                row.get('room_total', '-')
            ])
            
        csv_data = output.getvalue()
        output.close()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"allocation_{timestamp}.csv"
        
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        flash(f"Download failed: {str(e)}", "danger")
        return redirect(url_for('history'))

@app.route('/save', methods=['POST'])
def save_allocation_route():
    try:
        allocation_data = request.form.get('allocation_data')
        room_input = request.form.get('room_input')
        dept_input = request.form.get('dept_input')

        new_history = AllocationHistory(
            data=allocation_data,
            room_input=room_input,
            dept_input=dept_input
        )
        db.session.add(new_history)
        db.session.commit()
        
        maintain_history_limit()
        
        flash("Allocation saved successfully!", "success")
        return redirect(url_for('history'))
    except Exception as e:
        flash(f"Error saving: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/history')
def history():
    allocations = AllocationHistory.query.order_by(AllocationHistory.timestamp.desc()).all()
    # Parse JSON strings for display
    for alloc in allocations:
        alloc.parsed_data = json.loads(alloc.data)
    return render_template('history.html', history=allocations)

@app.route('/delete/<int:id>')
def delete_allocation(id):
    alloc = AllocationHistory.query.get_or_404(id)
    db.session.delete(alloc)
    db.session.commit()
    flash("Allocation deleted.", "info")
    return redirect(url_for('history'))

if __name__ == '__main__':
    app.run(debug=True)
