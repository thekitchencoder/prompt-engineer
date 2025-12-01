def process_user_data(users):
    """Process a list of user dictionaries and return statistics."""
    total = len(users)
    active_users = []

    for user in users:
        if user['status'] == 'active':
            active_users.append(user)

    avg_age = sum([u['age'] for u in users]) / total

    return {
        'total': total,
        'active': len(active_users),
        'average_age': avg_age
    }

# Usage
users = [
    {'name': 'Alice', 'age': 30, 'status': 'active'},
    {'name': 'Bob', 'age': 25, 'status': 'inactive'},
    {'name': 'Charlie', 'age': 35, 'status': 'active'}
]

stats = process_user_data(users)
print(stats)
