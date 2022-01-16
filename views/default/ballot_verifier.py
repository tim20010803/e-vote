####################################################################
# This is a python program that allows you to verify your ballot   #
# using the RSA algorithm. You do not need to download any package.#
# Please clone following text.                                     #
# Run "views\default\verify.py" and paste on to input them,        #
# then the output of this program will be "valid" or "invalid"     #
####################################################################

{{=XML(ballot.ballot_content)}}
{{=ballot.signature.split('-')[1]}}
{{=election.public_key.strip()}}

