"""Unavailable choices shared by form rendering and submission validation."""
UNAVAILABLE={
 'status':{'Married Filing Separately','Head of Household','Qualifying Surviving Spouse'},
 'dependent':{'Yes'}, 'blind':{'Yes'}, 'unsupported_income':{'Yes'},
 'needs_itemized':{'Yes'}, 'other_credit_needed':{'Yes'}, 'foreign':{'Yes'},
 'relationship':{'Other'}, 'own_support':{'Yes'}, 'resident':{'No'}, 'joint_return':{'Yes'},
}

def unavailable(key,value):
    return value in UNAVAILABLE.get(key,set())
