%global debug_package %{nil}
# macros for finding system files to update at install time (pci.ids, pcitable)
%define find() %(for f in %*; do if [ -e $f ]; then echo $f; break; fi; done)
%define _pciids   /usr/share/pci.ids        /usr/share/hwdata/pci.ids
%define _pcitable /usr/share/kudzu/pcitable /usr/share/hwdata/pcitable /dev/null
%define pciids    %find %{_pciids}
%define pcitable  %find %{_pcitable}

Name: i40e
Summary: Intel(R) 40-10 Gigabit Ethernet Connection Network Driver
Version: 2.22.8
Release: 2
Vendor: Intel Corporation
License: GPL-2.0
URL: http://support.intel.com
Source0: https://downloadmirror.intel.com/763931/%{name}-%{version}.tar.gz

Requires: kernel, findutils, gawk, bash, hwdata

BuildRequires: kernel-devel hwdata elfutils-devel uname-build-checks gcc

%description
This package contains the Intel(R) 40-10 Gigabit Ethernet Connection Network Driver.

%prep
%autosetup -n %{name}-%{version} -p1

%build
make -C src clean
make -C src

%install
make -C src INSTALL_MOD_PATH=%{buildroot} MANDIR=%{_mandir} modules_install mandocs_install
# Remove modules files that we do not want to include
find %{buildroot}/lib/modules/ -name 'modules.*' -exec rm -f {} \;
cd %{buildroot}
find lib -name "i40e.ko" \
	-fprintf %{_builddir}/%{name}-%{version}/file.list "/%p\n"


%clean
rm -rf %{buildroot}

%files -f file.list
%defattr(-,root,root)
%doc README file.list pci.updates
%license COPYING
%{_mandir}/man7/i40e.7.gz

%post
if [ -d /usr/local/share/%{name} ]; then
	rm -rf /usr/local/share/%{name}
fi
mkdir /usr/local/share/%{name}
cp --parents %{pciids} /usr/local/share/%{name}/
echo "original pci.ids saved in /usr/local/share/%{name}";
if [ "%{pcitable}" != "/dev/null" ]; then
	cp --parents %{pcitable} /usr/local/share/%{name}/
	echo "original pcitable saved in /usr/local/share/%{name}";
fi

LD="%{_docdir}/%{name}";
if [ -d %{_docdir}/%{name}-%{version} ]; then
	LD="%{_docdir}/%{name}-%{version}";
fi

#Yes, this really needs bash
bash -s %{pciids} \
	%{pcitable} \
	$LD/pci.updates \
	$LD/pci.ids.new \
	$LD/pcitable.new \
	%{name} \
<<"END"
#! /bin/bash
# Copyright (C) 2017 Intel Corporation
# For licensing information, see the file 'LICENSE' in the root folder
# $1 = system pci.ids file to update
# $2 = system pcitable file to update
# $3 = file with new entries in pci.ids file format
# $4 = pci.ids output file
# $5 = pcitable output file
# $6 = driver name for use in pcitable file

exec 3<$1
exec 4<$2
exec 5<$3
exec 6>$4
exec 7>$5
driver=$6
IFS=

# pattern matching strings
ID="[[:xdigit:]][[:xdigit:]][[:xdigit:]][[:xdigit:]]"
VEN="${ID}*"
DEV="	${ID}*"
SUB="		${ID}*"
TABLE_DEV="0x${ID}	0x${ID}	\"*"
TABLE_SUB="0x${ID}	0x${ID}	0x${ID}	0x${ID}	\"*"

line=
table_line=
ids_in=
table_in=
vendor=
device=
ids_device=
table_device=
subven=
ids_subven=
table_subven=
subdev=
ids_subdev=
table_subdev=
ven_str=
dev_str=
sub_str=

# force a sub-shell to fork with a new stdin
# this is needed if the shell is reading these instructions from stdin
while true
do
	# get the first line of each data file to jump start things
	exec 0<&3
	read -r ids_in
	if [ "$2" != "/dev/null" ];then
	exec 0<&4
	read -r table_in
	fi

	# outer loop reads lines from the updates file
	exec 0<&5
	while read -r line
	do
		# vendor entry
		if [[ $line == $VEN ]]
		then
			vendor=0x${line:0:4}
			ven_str=${line#${line:0:6}}
			# add entry to pci.ids
			exec 0<&3
			exec 1>&6
			while [[ $ids_in != $VEN ||
				 0x${ids_in:0:4} < $vendor ]]
			do
				echo "$ids_in"
				read -r ids_in
			done
			echo "$line"
			if [[ 0x${ids_in:0:4} == $vendor ]]
			then
				read -r ids_in
			fi

		# device entry
		elif [[ $line == $DEV ]]
		then
			device=`echo ${line:1:4} | tr "[:upper:]" "[:lower:]"`
			table_device=0x${line:1:4}
			dev_str=${line#${line:0:7}}
			ids_device=`echo ${ids_in:1:4} | tr "[:upper:]" "[:lower:]"`
			table_line="$vendor	$table_device	\"$driver\"	\"$ven_str|$dev_str\""
			# add entry to pci.ids
			exec 0<&3
			exec 1>&6
			while [[ $ids_in != $DEV ||
				 $ids_device < $device ]]
			do
				if [[ $ids_in == $VEN ]]
				then
					break
				fi
				if [[ $ids_device != ${ids_in:1:4} ]]
				then
					echo "${ids_in:0:1}$ids_device${ids_in#${ids_in:0:5}}"
				else
					echo "$ids_in"
				fi
				read -r ids_in
				ids_device=`echo ${ids_in:1:4} | tr "[:upper:]" "[:lower:]"`
			done
			if [[ $device != ${line:1:4} ]]
			then
				echo "${line:0:1}$device${line#${line:0:5}}"
			else
				echo "$line"
			fi
			if [[ $ids_device == $device ]]
			then
				read -r ids_in
			fi
			# add entry to pcitable
			if [ "$2" != "/dev/null" ];then
			exec 0<&4
			exec 1>&7
			while [[ $table_in != $TABLE_DEV ||
				 ${table_in:0:6} < $vendor ||
				 ( ${table_in:0:6} == $vendor &&
				   ${table_in:7:6} < $table_device ) ]]
			do
				echo "$table_in"
				read -r table_in
			done
			echo "$table_line"
			if [[ ${table_in:0:6} == $vendor &&
			      ${table_in:7:6} == $table_device ]]
			then
				read -r table_in
			fi
			fi
		# subsystem entry
		elif [[ $line == $SUB ]]
		then
			subven=`echo ${line:2:4} | tr "[:upper:]" "[:lower:]"`
			subdev=`echo ${line:7:4} | tr "[:upper:]" "[:lower:]"`
			table_subven=0x${line:2:4}
			table_subdev=0x${line:7:4}
			sub_str=${line#${line:0:13}}
			ids_subven=`echo ${ids_in:2:4} | tr "[:upper:]" "[:lower:]"`
			ids_subdev=`echo ${ids_in:7:4} | tr "[:upper:]" "[:lower:]"`
			table_line="$vendor	$table_device	$table_subven	$table_subdev	\"$driver\"	\"$ven_str|$sub_str\""
			# add entry to pci.ids
			exec 0<&3
			exec 1>&6
			while [[ $ids_in != $SUB ||
				 $ids_subven < $subven ||
				 ( $ids_subven == $subven && 
				   $ids_subdev < $subdev ) ]]
			do
				if [[ $ids_in == $VEN ||
				      $ids_in == $DEV ]]
				then
					break
				fi
				if [[ ! (${ids_in:2:4} == "1014" &&
					 ${ids_in:7:4} == "052C") ]]
				then
					if [[ $ids_subven != ${ids_in:2:4} || $ids_subdev != ${ids_in:7:4} ]]
					then
						echo "${ids_in:0:2}$ids_subven $ids_subdev${ids_in#${ids_in:0:11}}"
					else
						echo "$ids_in"
					fi
				fi
				read -r ids_in
				ids_subven=`echo ${ids_in:2:4} | tr "[:upper:]" "[:lower:]"`
				ids_subdev=`echo ${ids_in:7:4} | tr "[:upper:]" "[:lower:]"`
			done
			if [[ $subven != ${line:2:4} || $subdev != ${line:7:4} ]]
			then
				echo "${line:0:2}$subven $subdev${line#${line:0:11}}"
			else
				echo "$line"
			fi
			if [[ $ids_subven == $subven  &&
			      $ids_subdev == $subdev ]]
			then
				read -r ids_in
			fi
			# add entry to pcitable
			if [ "$2" != "/dev/null" ];then
			exec 0<&4
			exec 1>&7
			while [[ $table_in != $TABLE_SUB ||
				 ${table_in:14:6} < $table_subven ||
				 ( ${table_in:14:6} == $table_subven &&
				   ${table_in:21:6} < $table_subdev ) ]]
			do
				if [[ $table_in == $TABLE_DEV ]]
				then
					break
				fi
				if [[ ! (${table_in:14:6} == "0x1014" &&
					 ${table_in:21:6} == "0x052C") ]]
				then
					echo "$table_in"
				fi
				read -r table_in
			done
			echo "$table_line"
			if [[ ${table_in:14:6} == $table_subven &&
			      ${table_in:21:6} == $table_subdev ]]
			then
				read -r table_in
			fi
			fi
		fi

		exec 0<&5
	done

	# print the remainder of the original files
	exec 0<&3
	exec 1>&6
	echo "$ids_in"
	while read -r ids_in
	do
		echo "$ids_in"
	done

	if [ "$2" != "/dev/null" ];then
	exec 0>&4
	exec 1>&7
	echo "$table_in"
	while read -r table_in
	do
		echo "$table_in"
	done
	fi

	break
done <&5

exec 3<&-
exec 4<&-
exec 5<&-
exec 6>&-
exec 7>&-

END

mv -f $LD/pci.ids.new  %{pciids}
if [ "%{pcitable}" != "/dev/null" ]; then
	mv -f $LD/pcitable.new %{pcitable}
fi

uname -r | grep BOOT || /sbin/depmod -a > /dev/null 2>&1 || true

if which dracut >/dev/null 2>&1; then
	echo "Updating initramfs with dracut..."
	if dracut --force ; then
		echo "Successfully updated initramfs."
	else
		echo "Failed to update initramfs."
		echo "You must update your initramfs image for changes to take place."
		exit -1
	fi
elif which mkinitrd >/dev/null 2>&1; then
	echo "Updating initrd with mkinitrd..."
	if mkinitrd; then
		echo "Successfully updated initrd."
	else
		echo "Failed to update initrd."
		echo "You must update your initrd image for changes to take place."
		exit -1
	fi
else
	echo "Unable to determine utility to update initrd image."
	echo "You must update your initrd manually for changes to take place."
	exit -1
fi

%preun
rm -rf /usr/local/share/%{name}

%postun
uname -r | grep BOOT || /sbin/depmod -a > /dev/null 2>&1 || true

if which dracut >/dev/null 2>&1; then
	echo "Updating initramfs with dracut..."
	if dracut --force ; then
		echo "Successfully updated initramfs."
	else
		echo "Failed to update initramfs."
		echo "You must update your initramfs image for changes to take place."
		exit -1
	fi
elif which mkinitrd >/dev/null 2>&1; then
	echo "Updating initrd with mkinitrd..."
	if mkinitrd; then
		echo "Successfully updated initrd."
	else
		echo "Failed to update initrd."
		echo "You must update your initrd image for changes to take place."
		exit -1
	fi
else
	echo "Unable to determine utility to update initrd image."
	echo "You must update your initrd manually for changes to take place."
	exit -1
fi

%changelog
* Thu Feb 2 2023 chengyechun <chengyechun1@huawei.com> - 2.22.8-2
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:remove i40e-2.14.13.tar.gz

* Thu Feb 2 2023 chengyechun <chengyechun1@huawei.com> - 2.22.8-1
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:Update i40e version to 2.22.8 to fix kernel-6.1 based build error

* Wed Jun 22 2022 chengyechun <chengyechun1@huawei.com> - 2.14.13-9
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:extend ringparam setting/getting API with rx_buf_len

* Mon Jun 13 2022 chengyechun <chengyechun1@huawei.com> - 2.14.13-8
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:extend coalesce setting uAPI with CQE mode

* Sat Oct 30 2021 Aichun Li <liaichun@huawei.com> - 2.14.13-7
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:rollback fix ATR queue selection

* Fri Oct 29 2021 Aichun Li <liaichun@huawei.com> - 2.14.13-6
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:fix ATR queue selection

* Wed Jul 7 2021 gaihuiying <gaihuiying1@huawei.com> - 2.14.13-5
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:add dependency gcc

* Tue Jul 6 2021 gaihuiying <gaihuiying1@huawei.com> - 2.14.13-4
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:add dependency uname-build-checks
       fix hang when install i40e in docker

* Fri Mar 19 2021 kwb0523 <kwb0523@163.com> - 2.14.13-3
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:fix install problem

* Fri Feb 5 2021 hanzhijun <hanzhijun1@huawei.com> - 2.14.13-2 
- Type:bugfix
- ID:NA
- SUG:NA
- DESC:fix gcc9 warning -Werror=implicit-function-declaration

* Tue Feb 2 2021 seuzw <930zhaowei@163.com> - 2.14.13-1
- Package init
