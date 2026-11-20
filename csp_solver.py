
import copy

# CSP (Constraint Satisfaction Problem) Components Explanation:
#
# 1. Variables:
#    - The variables in this CSP are the departments that need to be allocated to exam rooms.
#
# 2. Domain:
#    - The domain for each variable (department) is the set of available exam rooms.
#    - A department can be split across multiple rooms, so an assignment is not just one room
#      but a number of students assigned to a room.
#
# 3. Constraints:
#    - All students from every department must be allocated.
#    - The number of students in any given room must not exceed its capacity.
#
# 4. Search Strategy:
#    - The problem is solved using a backtracking search algorithm.
#    - It recursively tries to allocate students to rooms and backtracks if a
#      path leads to a state where constraints cannot be met.
#
# 5. Heuristic (Variable Ordering):
#    - We use a heuristic: "select the department with the largest number of unallocated students first."
#      This prioritizes the most constrained variables, aiming to fail early and prune the search space.

def is_consistent(room, num_students):
    """
    Constraint checking function.
    Checks if assigning a certain number of students to a room is valid.
    """
    return room['remaining_capacity'] >= num_students

def select_unassigned_variable(departments):
    """
    Selects the next department to assign using a heuristic.
    Heuristic: Choose the department with the largest number of remaining students.
    """
    largest_dept = None
    max_remaining = -1
    for dept in departments:
        if dept['remaining_students'] > max_remaining:
            max_remaining = dept['remaining_students']
            largest_dept = dept
    return largest_dept if max_remaining > 0 else None

def backtracking_search(departments, rooms, allocation):
    """
    Main backtracking function to solve the CSP.
    """
    # Base case: If all students are allocated, a solution is found.
    if all(d['remaining_students'] == 0 for d in departments):
        return allocation

    # Heuristic: Select the department with the most students left to allocate.
    dept = select_unassigned_variable(departments)
    if not dept:
        return None 

    original_remaining_students = dept['remaining_students']
    dept_roll_number_start = dept['students'] - original_remaining_students + 1

    # Iterate through the domain (rooms) for the selected variable (department).
    for room in rooms:
        if room['remaining_capacity'] > 0:
            # Determine how many students to try assigning to this room.
            students_to_assign = min(original_remaining_students, room['remaining_capacity'])

            if students_to_assign > 0 and is_consistent(room, students_to_assign):
                # Apply the assignment
                dept['remaining_students'] -= students_to_assign
                room['remaining_capacity'] -= students_to_assign
                
                roll_range = f"{dept_roll_number_start}-{dept_roll_number_start + students_to_assign - 1}"
                
                allocation.append({
                    'room': room['name'],
                    'block': room.get('block', '-'),
                    'floor': room.get('floor', '-'),
                    'dept': dept['name'],
                    'sec': dept['section'],
                    'roll_no_range': roll_range,
                    'num_students': students_to_assign
                })

                # Recur for the next assignment
                result = backtracking_search(departments, rooms, allocation)
                if result is not None:
                    return result

                # Backtrack: Undo the assignment
                allocation.pop()
                dept['remaining_students'] += students_to_assign
                room['remaining_capacity'] += students_to_assign
    
    return None

def solve_allocation(rooms_input, departments_input):
    """
    Wrapper function to prepare data and solve the CSP.
    """
    rooms = copy.deepcopy(rooms_input)
    departments = copy.deepcopy(departments_input)

    for room in rooms:
        room['remaining_capacity'] = int(room['capacity'])
    
    for dept in departments:
        dept['remaining_students'] = int(dept['students'])
        dept['students'] = int(dept['students'])

    total_students = sum(d['remaining_students'] for d in departments)
    total_capacity = sum(r['remaining_capacity'] for r in rooms)

    if total_students > total_capacity:
        return None, "Not enough room capacity for all students."

    solution = backtracking_search(departments, rooms, [])
    if solution:
        solution.sort(key=lambda x: (x['room'], x['dept']))
        return solution, None
    else:
        return None, "No valid allocation found."
