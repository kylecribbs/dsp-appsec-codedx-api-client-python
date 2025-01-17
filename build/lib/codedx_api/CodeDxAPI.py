from codedx_api.APIs import ProjectsAPI, ReportsAPI, JobsAPI, AnalysisAPI, ActionsAPI, FindingsAPI
import time
import json

report_columns = [
	"projectHierarchy",
	"id",
	"creationDate",
	"updateDate",
	"severity",
	"status",
	"cwe",
	"rule",
	"tool",
	"location",
	"element",
	"loc.path",
	"loc.line"
]

class CodeDx(ProjectsAPI.Projects, ReportsAPI.Reports, JobsAPI.Jobs, AnalysisAPI.Analysis, ActionsAPI.Actions, FindingsAPI.Findings):
	def __init__(self, base, api_key, verbose=False):
		"""Create a codeDx APIclient."""
		super().__init__(base, api_key, verbose)

	def download_report(self, data, file_name):
		"""Saves the report in a file."""
		self.type_check(file_name, str, "Filename")
		with open(file_name, 'w') as f:
			try:
				f.write(json.dumps(data))
			except:
				f.write(data.decode("utf-8"))
		return f

	def wait_for_job(self, job, msg):
		job["status"] = "queued"
		while job["status"] != "completed":
			print(msg)
			time.sleep(5)
			print(f"{msg} - Checking again in 5 seconds.")
			job = self.job_status(job["jobId"])
		return job

	def get_report(self, job, content_type, file_name, msg):
		"""Get the project report from Code DX."""
		self.wait_for_job(job, msg)
		print("Downloading report...")
		print(content_type)
		res = self.job_result(job["jobId"], accept=content_type)
		file = self.download_report(res, file_name)
		return file

	def get_pdf(self, proj, summary_mode="simple", details_mode="with-source", include_result_details=False, include_comments=False, include_request_response=False, file_name='report.pdf', filters=None):
		"""Download a project report in PDF format."""
		if not filters: filters = {}
		job = self.generate_pdf(proj, summary_mode, details_mode, include_result_details, include_comments, include_request_response, filters)
		res = self.get_report(job, 'application/pdf', file_name, "Waiting for report generation...")
		return res

	def get_csv(self, proj, cols=None, file_name='report.csv'):
		"""Download a project report in CSV format."""
		if not cols: cols = report_columns
		job = self.generate_csv(proj, cols)
		res = self.get_report(job, 'text/csv', file_name, "Waiting for report generation...")
		return res

	def get_xml(self, proj, include_standards=False, include_source=False, include_rule_descriptions=True, file_name='report.xml'):
		""" Allows user to queue a job to generate an xml report.

			Args:
				include_standards <Boolean>: List standards violations. Default is fault.
				include_source <Boolean>: Include source code snippets. Default is false.
				include_rule_descriptions <Boolean>: Include rule descriptions. Default is true.

			Returns jobId and status.
			
		"""
		job = self.generate_xml(proj, include_standards, include_source, include_rule_descriptions)
		res = self.download_report(job, file_name)
		return res

	def get_nessus(self):
		pass

	def get_nbe(self):
		pass

	def analyze(self, proj, file_name):
		"""Upload a vulnerability scan and run an analysis."""
		print("Creating analysis...")
		prep = self.create_analysis(proj)
		prep_id = prep["prepId"]
		print("Uploading report...")
		ext_analysis = self.upload_analysis(prep_id, file_name)
		self.wait_for_job(ext_analysis, "Analyzing external report content...")
		prep = self.get_prep(prep_id)
		if 'verificationErrors' in prep and len(prep['verificationErrors']) > 0:
			print("Verification Errors:")
			for error in prep['verificationErrors']:
				print(error)
			raise Exception("Fix verification errors...")
		else:
			analysis_job = self.run_analysis(prep_id)
			self.wait_for_job(analysis_job, "Running analysis...")
			analysis = self.get_analysis(proj, analysis_job["analysisId"])
			print("Analysis complete.")
			return analysis

	def update_statuses(self, proj, status="false-positive", filters=None):
		if not filters: filters = {}
		print("Updating bulk statuses...")
		job = self.bulk_status_update(proj, status, filters)
		self.wait_for_job(job, "Waiting for statuses to update...")
		msg = "Bulk status update (%s) for project %s" % (status, proj)
		print(msg)
