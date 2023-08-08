import dropbox
import dropbox.team
import asyncio
import time

class DropboxRequest:
    def __init__(self):
        self.access_token = self._get_access_token()
        self.dbx = dropbox.DropboxTeam(self.access_token)

        #The following info is retreived from the Dropbox Developer page in your project
        self.APP_KEY = ""
        self.APP_SECRET = ""

        #some actions must be taken by through the 'admin' and some as a 'user' but they can use the same email
        self.admin_email = ""
        id = dropbox.team.UserSelectorArg.email(self.admin_email).id
        self.admin = self.dbx.as_admin(id)  
        self.user = self.dbx.as_user(id)  
           
    def _get_access_token(self):
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(self.APP_KEY, self.APP_SECRET)
        authorize_url = auth_flow.start()

        print(f"1. Go to: {authorize_url}")
        print("2. Click 'Allow' (you might have to log in with your Dropbox account).")
        print("3. Copy the authorization code.")
        auth_code = input("Enter the authorization code here: ").strip()

        try:
            oauth_result = auth_flow.finish(auth_code)
            access_token = oauth_result.access_token
            return access_token
        except dropbox.dropbox_client.BadInputException as e:
            print(f"Error during authentication: {e}")
            return None

    async def _create_group(self, group_name):
        def sync_create_group():
            try:
                response = self.dbx.team_groups_create(group_name)
                group_id = response.group_id
                return group_id
            except dropbox.exceptions.ApiError as e:
                print(f'Error occurred during group creation: {e}')
                return None
        return await asyncio.to_thread(sync_create_group)

    async def _add_member_to_group(self, email, group_id):
        def sync_add_member_to_group():
            try:
                group = dropbox.team.GroupSelector.group_id(group_id)
                selected_user = dropbox.team.UserSelectorArg.email(email)
                member_access = dropbox.team.MemberAccess(
                    user=selected_user,
                    access_type=dropbox.team.GroupAccessType.member
                )
                print("Add member call")
                add_request = self.dbx.team_groups_members_add(group, [member_access])
                while(not self.dbx.team_groups_job_status_get(add_request.async_job_id).is_complete()):
                    print(self.dbx.team_groups_job_status_get(add_request.async_job_id))

                print(f"Add member return")

                return True
            except dropbox.exceptions.ApiError as e:
                print(f'Error occurred while adding a member to the group: {e}')
                return False
            
        await asyncio.to_thread(sync_add_member_to_group)

    def _remove_member_from_group(self, email, group_id):
        try:
            group = dropbox.team.GroupSelector.group_id(group_id)
            selected_user = dropbox.team.UserSelectorArg.email(email)
            self.dbx.team_groups_members_remove(group, [selected_user])

            return True
        except dropbox.exceptions.ApiError as e:
            print(f'Error occurred while removing a member from the group: {e}')
            return False

    async def _create_folder(self, folder_name):
        def sync_create_folder():
            try:
                folder = self.dbx.team_team_folder_create(folder_name)
                return folder.team_folder_id
            except dropbox.exceptions.ApiError as e:
                print(f'Error occurred during folder creation: {e}')
                return None
        return await asyncio.to_thread(sync_create_folder)

    async def _share_folder_with_group(self, folder_id, group_id, can_edit):
        def sync_share_folder_with_group():
            try:
                selected_group = dropbox.sharing.MemberSelector.dropbox_id(group_id)
                if can_edit:
                    target_access_level = dropbox.sharing.AccessLevel.editor
                else:
                    target_access_level = dropbox.sharing.AccessLevel.viewer

                add_group_member = dropbox.sharing.AddMember(
                    member=selected_group,
                    access_level=target_access_level
                )
                print(f"{group_id} share call")
                self.admin.sharing_add_folder_member(
                    shared_folder_id=folder_id,
                    members=[add_group_member]
                )
                print(f"{group_id} share return")
                return True
            except dropbox.exceptions.ApiError as e:
                print(f'Error occurred while sharing the folder with the group: {e}')
                return False

        await asyncio.to_thread(sync_share_folder_with_group)

    async def _share_folder(self, path):
        def sync_share_folder():
            share_launch = self.admin.sharing_share_folder(path)
            while(not self.admin.sharing_check_share_job_status(share_launch.get_async_job_id()).is_complete()):
                print(self.admin.sharing_check_share_job_status(share_launch.get_async_job_id()))

            #dropbox_request.admin.sharing_add_folder_member()
            data = self.admin.files_get_metadata(path)
            return data.shared_folder_id
        return await asyncio.to_thread(sync_share_folder)

    async def _restrict_inheritance(self, parent_folder_id, subfolder_id):
        def sync__restrict_inheritance():
            print(f"{parent_folder_id} update inheritance call")
            access_launch = self.user.sharing_set_access_inheritance(subfolder_id, dropbox.sharing.AccessInheritance.no_inherit)

            while(not self.admin.sharing_check_share_job_status(access_launch.get_async_job_id()).is_complete()):
                print(self.admin.sharing_check_share_job_status(access_launch.get_async_job_id()))

            sfMembers = self.user.sharing_list_folder_members(parent_folder_id)
            for group in sfMembers.groups:
                selected_group = dropbox.sharing.MemberSelector.dropbox_id(group.group.group_id)
                target_access_level = dropbox.sharing.AccessLevel.viewer

                add_group_member = dropbox.sharing.AddMember(
                    member=selected_group,
                    access_level=target_access_level
                )
                print(f"reshare call")
                self.admin.sharing_add_folder_member(
                    shared_folder_id=subfolder_id,
                    members=[add_group_member]
                )
                print(f"reshare return")
            print(f"{parent_folder_id} update inheritance return")
        return await asyncio.to_thread(sync__restrict_inheritance)  

    async def _get_group_id(self, group_name):
        def sync_get_group_id():
            # get group from list of 1000
            groupsListResult = self.dbx.team_groups_list()
            while True:

                for group in groupsListResult.groups:
                    if group.group_name == group_name:
                        target_group_id = group.group_id
                        return target_group_id
                if not groupsListResult.has_more:
                    break
                groupsListResult = self.dbx.team_groups_list_continue(groupsListResult.cursor)
                
            print(f"Could not find group {group_name}")
            
            return
        return await asyncio.to_thread(sync_get_group_id)  

    async def _create_folders_async(self, folder_name, template):
        async def create_folder(folder_name, folder):
            def sync_create_folder(folder_name, folder):
                print(f"{folder} create call")
                data = self.user.files_create_folder(f"/{folder_name}/{folder}")
                if data.parent_shared_folder_id:
                    print(f"{folder} created")
                else:
                    print(f"{folder} not created: {data}")

            await asyncio.to_thread(sync_create_folder, folder_name, folder)

        tasks = [create_folder(folder_name, folder) for folder in template]
        await asyncio.gather(*tasks)

    async def _init_project_async(self, pm_name, field_name):
        group_names = ["Executive", "Purchasing", "Accounting", "VDC", "Final Contracts", "Safety"]
        tasks = [self._get_group_id(group_name) for group_name in group_names]
        tasks.append(self._create_group(pm_name))
        tasks.append(self._create_group(field_name))
        tasks.append(self._create_folder(pm_name))
        tasks.append(self._create_folder(field_name))
        ids = await asyncio.gather(*tasks)
        return ids

    async def createProject(self, project_number, project_name, pm_email , supe_email):
        field_template = ["As-Builts", "Daily Reports", "Drawings & Specifications", "Jobsite Photos", "Material Purchasing", "Meeting Minutes", "Permits", "Prefab", "Prefab Install", "Project Schedules", "Quality Control", "Safety", "Submittals & Shop Drawings"]
        pm_template = ["Billings", "Change Proposals", "CIP Documents", "Close Out Documents", "Contract & Change Orders", "Contracts and Change Orders – FINAL", "Job Invoice", "Labor Projections", "Owner Purchase Orders", "Project Estimate - Takeoffs & Quotes", "Projections", "RFI's", "Subcontracts", "Transmittals"]
        
        pm_name = f"{project_number} - {project_name} - PM"
        field_name = f"{project_number} - {project_name} - Field"

        # Record the start time
        start_time = time.time()

        # Fetch group IDs asynchronously
        ids = await self._init_project_async(pm_name, field_name)

        # Unpack the group_ids list
        executive_id, purchasing_id, accounting_id, vdc_id, contracts_id, safety_id, pm_group_id, field_group_id, pm_folder_id, field_folder_id = ids
        await self._add_member_to_group(self.admin_email, pm_group_id)

        pre_share_tasks = [
            self._share_folder_with_group(pm_folder_id, pm_group_id, True),
            self._share_folder_with_group(field_folder_id, pm_group_id, True)
        ]

        await asyncio.gather(*pre_share_tasks)
        # share folders async
        share_tasks = [
            self._share_folder_with_group(pm_folder_id, contracts_id, False),
            self._share_folder_with_group(pm_folder_id, executive_id, True),
            self._share_folder_with_group(pm_folder_id, purchasing_id, True),
            self._share_folder_with_group(pm_folder_id, accounting_id, True),
            
            self._share_folder_with_group(field_folder_id, executive_id, True),
            self._share_folder_with_group(field_folder_id, purchasing_id, True),
            self._share_folder_with_group(field_folder_id, accounting_id, True),
            self._share_folder_with_group(field_folder_id, vdc_id, True),    
            self._share_folder_with_group(field_folder_id, safety_id, False),
            self._share_folder_with_group(field_folder_id, field_group_id, True),
                
            self._add_member_to_group(pm_email, pm_group_id),
            self._add_member_to_group(pm_email, field_group_id),
            self._add_member_to_group(supe_email, field_group_id),

            self._create_folders_async(pm_name, pm_template),
            self._create_folders_async(field_name, field_template)
        ]
        await asyncio.gather(*share_tasks)

        subfolder_tasks = [
            self._share_folder(f"/{field_name}/Safety"),
            self._share_folder(f"/{pm_name}/Contracts and Change Orders – FINAL")
        ]
        safety_folder_id, ccof_folder_id = await asyncio.gather(*subfolder_tasks)

        await self._restrict_inheritance(pm_folder_id, ccof_folder_id)

        reshare_tasks = [
            self._share_folder_with_group(ccof_folder_id, contracts_id, True),
            self._share_folder_with_group(ccof_folder_id, executive_id, True),
            self._share_folder_with_group(safety_folder_id, safety_id, True)
        ]

        await asyncio.gather(*reshare_tasks)

        # remove add "user" to PM group
        self.user.sharing_relinquish_folder_membership(ccof_folder_id)
        self._remove_member_from_group(self.admin_email, pm_group_id)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\n==================================================\nDropbox Project created in {elapsed_time:.2f} seconds.\n==================================================\n")

        
        print("Done")