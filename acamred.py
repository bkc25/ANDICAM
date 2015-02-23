#!/scisoft/bin/python
#pyraf equivalents of speedup.cl, processccd.cl, combflat.cl, CCDsort.cl, and IRsort.cl
#these functions mirror their iraf counterparts pretty closesly, and function in the same way
#the pyraf wrapper prevents caching problems and lets us easily change directories, execute functions etc
#some projects have special places to pick up data, like the blazar group
#the photometric standards, xrb group, and bethany. specific checks are made for those data
import pyfits
import os
import fnmatch
import glob
from pyraf import iraf
iraf.prcacheOff()

#dont use this, its still under construction
def domecalibs(band):
	bandcomb=iraf.ls("*.dome"+band+".fits", Stdout=1)
	if len(bandframes) == 1:
		return
	elif len(bandframes) == 0:
		banduncomb=iraf.ls("dome"+band+".*.fits", Stdout=1)
		if len(banduncomb) != 10:
			oldband=iraf.ls("/data/yalo180/yalo/SMARTS13m/PROCESSEDCALS/ccd*.dome"+band+".fits", Stdout=1)
			iraf.imcopy(oldband[-1], output='.')
		return

#make a combined b skyflat. 
#Requires: a bias image in same directory to do the bias subtraction
#	skyflats must be offset and have appropriate count number
#input: the date the skyflats were observed YYMMDD
#output: flat.B, a text file that lists the names of the skyflat fits files
#	ccdYYMMDD.skyflatB.fits, the combined skyflat
def skyflat(date, low=15000, high=22000, numimages=5):
	#check if biases are in this directory
	if len(glob.glob('*.bias.*')) < 1:
		print "no combined bias found, exiting"
		return
	#get image name and mean pixel value for all skyflat images
	stats=iraf.imstat('*sky*',format=False,fields='image,mean',Stdout=1)
	pairs=[i.split() for i in stats]

	#write the names of the skyflats w right ammount of counts to file
	#keep track of how many good ones there are
	goodCount=0
	with open("flat.B",'w') as FB:
		for i in pairs:
			if float(i[1]) > low and float(i[1]) < high:
				FB.write(i[0]+'\n')
				goodCount+=1

	if goodCount < numimages:
		print "only "+str(goodCount)+" skyflats have counts between "+str(low)+" and "+str(high)
		print "no combined skyflat made"
		return
	else:
		iraf.ccdproc(images="@flat.B",output=" ",fixpix="no",overscan="yes",trim="no",zerocor="yes",darkcor="no",flatcor="no",illumcor="no",fringecor="no",readcor="no",scancor="no",readaxis="line",biassec="[3:14,1:1024]",zero="*.bias.fits",interactive="no",functio="spline3",order=11)
		iraf.flatcombine("@flat.B",output="FLAT",combine="median",reject="minmax",process="no",scale="mode",ccdtype="")
		os.system("mv FLAT.fits ccd"+str(date)+".skyflatB.fits")
		print ("made combined skyflat ccd"+str(date)+".skyflatB.fits")
	return

def optdomecomb2(date, fwheel):
	if len(glob.glob('*bias*')) < 1:
		print "no biases found, exiting"
		return

	elif fwheel=='bias':
		biaslist=glob.glob('*bias.[0-9]*')
		if len(biaslist) > 10:
			print "only "+str(len(biaslist))+" biases found. you need at least 10"
		else:
			with open("bias.list",'w') as BILIS:
				for i in biaslist:
					BILIS.write(i+'\n')
			iraf.zerocombine("@bias.list",output="ccd"+str(date)+".bias.fits",combine="average",reject="minmax",scale="none",ccdtype="",process="no",delete="no",clobber="no",nlow=1,nhigh=1,nkeep=1)
			print "created ccd"+str(date)+".bias.fits"
		return

	elif fwheel in ['B','V','R','I']:
		domelist=glob.glob('*dome'+fwheel+'.[0-9]*')
		if len(domelist) < 1:
			print 'no '+fwheel+' domes found'
		elif len(domelist) > 10:
			print 'only '+str(len(domelist))+' domes found. you need at least 10'
		else:
			with open('flat'+fwheel+'.list', 'w') as flist:
				for i in domelist:
					flist.write(i+'\n')
			iraf.ccdproc("@flat"+flist+".list", output="z@flat"+flist+".list",ccdtype=" ",noproc="no", fixpix="no",overscan="yes", trim="no", zerocor="yes",darkcor="no",flatcor="no", illumcor="no", fringec="no", readcor="no", scancor="no", readaxis="line", biassec="[3:14,1:1024]", zero="ccd"+str(date)+".bais.fits", interactive="no", functio="spline3", order=11)
			iraf.flatcombine("z@flat"+flist+".list", output="ccd"+str(date)+".dome"+flist+".fits",combine="average", reject="crreject", ccdtype="", process="no", subsets="no", delete="no", clobber="no", scale="mode", rdnoise=6.5, gain=2.3)
			os.system('rm z*dome'+flist+'*fits')
			print "created ccd"+str(date)+".dome"+flist+".fits"
		return

	else:
		print "your input for the filter was not recognized. Please use either 'bias', 'B', 'V', 'R', or 'I' and try again"
		return

#combine biases and optical domes
#Requires: the uncombined fits images
#	if you are combining a dome, you must have a bias from the same night as the dome to preform appropriate bias subtraction
#Input: the date the domes were observed YYMMDD
#Outupt: combined dome fits frame for each color where uncombined frames are in the directory 
def optdomecomb(date):
	os.system("ls *bias* > bias.list")
	with open("bias.list") as BILIS:
		bilis=BILIS.read()
	if len(bilis.split('\n'))-1 > 1:
		print str(len(bilis.split('\n'))-1)+" biases found"
		iraf.zerocombine("@bias.list",output="ccd"+str(date)+".bias.fits",combine="average",reject="minmax",scale="none",ccdtype="",process="no",delete="no",clobber="no",nlow=1,nhigh=1,nkeep=1)
	else:
		print "no biases found"
	
	os.system("ls *domeV* > flatv.list")
	with open("flatv.list") as FLVLIS:
		flvlis=FLVLIS.read()
	if len(flvlis.split('\n'))-1 > 1:
		print str(len(flvlis.split('\n'))-1)+" *domeV* found"
		iraf.ccdproc("@flatv.list", output="z@flatv.list",ccdtype=" ",noproc="no", fixpix="no",overscan="yes", trim="no", zerocor="yes",darkcor="no",flatcor="no", illumcor="no", fringec="no", readcor="no", scancor="no", readaxis="line", biassec="[3:14,1:1024]", zero="ccd"+str(date)+".bais.fits", interactive="no", functio="spline3", order=11)
		iraf.flatcombine("z@flatv.list", output="ccd"+str(date)+".domeV.fits",combine="average", reject="crreject", ccdtype="", process="no", subsets="no", delete="no", clobber="no", scale="mode", rdnoise=6.5, gain=2.3)
		os.system("rm z*domeV*fits")
	else:
		print "no V domes found"

	os.system("ls *domeR* > flatr.list")
	with open("flatr.list") as FLRLIS:
		flrlis=FLRLIS.read()
	if len(flrlis.split('\n'))-1 > 1:
		print str(len(flrlis.split('\n'))-1)+" *domeR* found"
		iraf.ccdproc("@flatr.list", output="z@flatr.list",ccdtype=" ",noproc="no", fixpix="no",overscan="yes", trim="no", zerocor="yes",darkcor="no",flatcor="no", illumcor="no", fringec="no", readcor="no", scancor="no", readaxis="line", biassec="[3:14,1:1024]", zero="ccd"+str(date)+".bais.fits", interactive="no", functio="spline3", order=11)
		iraf.flatcombine("z@flatr.list", output="ccd"+str(date)+".domeR.fits",combine="average", reject="crreject", ccdtype="", process="no", subsets="no", delete="no", clobber="no", scale="mode", rdnoise=6.5, gain=2.3)
		os.system("rm z*domeR*fits")
	else:
		print "no R domes found"
	
	os.system("ls *domeI* > flati.list")
	with open("flati.list") as FLILIS:
		flilis=FLILIS.read()
	if len(flilis.split('\n'))-1 > 1:
		print str(len(flilis.split('\n'))-1)+" *domeI* found"
		iraf.ccdproc("@flati.list", output="z@flati.list",ccdtype=" ",noproc="no", fixpix="no",overscan="yes", trim="no", zerocor="yes",darkcor="no",flatcor="no", illumcor="no", fringec="no", readcor="no", scancor="no", readaxis="line", biassec="[3:14,1:1024]", zero="ccd"+str(date)+".bais.fits", interactive="no", functio="spline3", order=11)
		iraf.flatcombine("z@flati.list", output="ccd"+str(date)+".domeI.fits",combine="average", reject="crreject", ccdtype="", process="no", subsets="no", delete="no", clobber="no", scale="mode", rdnoise=6.5, gain=2.3)
		os.system("rm z*domeI*fits")
	else:
		print "no I domes found"
	os.system("rm flat{v,r,i}.list")
	os.system("rm bias.list")
	return

#although ANDICAM no longer takes U data, it is simpler
#to create dummy U lists in.U and out.U and keep using 
#pre existing .cl scripts than to rewrite everything
#prepares optical images for reduction
#requires: skyflatB, ccd domes, ccd bias, ccd data, in directory when function is run
#input: none
#output: in.{B,V,R,I}, are txt files which list images observed in b,v,r, and i filters
#	out.{B,V,R,I}, are txt files which list the names of those in in* after they are reduced
def speedup():
	#the observer may have forgotten to delete focus, trim, and junk frames
	if len(glob.glob('*junk*')) > 0:
		os.system('rm *junk*')
	if len(glob.glob('*foco*')) > 0:
		os.system('rm *foco*')
	if len(glob.glob('*trim*')) > 0:
		os.system("rm *trim*")
	
	os.system("mkdir calibs")
	os.system("mv *bias* calibs")
	os.system("mv *ky* calibs")
	os.system("mv *dome* calibs")
	rawimages=fnmatch.filter(os.listdir('.'),'ccd*.fits')
	inU=[i for i in rawimages if (pyfits.open(i)[0].header['ccdfltid'] =='U')]
	with open("in.U",'w') as U:
		for i in inU:
			U.write(i+'\n')
	inB=[i for i in rawimages if (pyfits.open(i)[0].header['ccdfltid'] =='B')]
	with open("in.B",'w') as B:
		for i in inB:
			B.write(i+'\n')
	inV=[i for i in rawimages if (pyfits.open(i)[0].header['ccdfltid'] =='V' or pyfits.open(i)[0].header['ccdfltid'] =='V+ND4')]
	with open("in.V",'w') as V:
		for i in inV:
			V.write(i+'\n')
	inR=[i for i in rawimages if (pyfits.open(i)[0].header['ccdfltid'] =='R')]
	with open("in.R",'w') as R:
		for i in inR:
			R.write(i+'\n')
	inI=[i for i in rawimages if (pyfits.open(i)[0].header['ccdfltid'] =='I' or pyfits.open(i)[0].header['ccdfltid'] =='I+ND4')]
	with open("in.I",'w') as I:
		for i in inI:
			I.write(i+'\n')
	#iraf.hselect(images="ccd*",fields="$I", expr='ccdfltid?="U"', Stdout="in.U")	#U data is not taken anymore
	#iraf.hselect(images="ccd*",fields="$I", expr='ccdfltid?="B"', Stdout="in.B")
	#iraf.hselect(images="ccd*",fields="$I", expr='ccdfltid?="V"', Stdout="in.V")
	#iraf.hselect(images="ccd*",fields="$I", expr='ccdfltid?="R"', Stdout="in.R")
	#iraf.hselect(images="ccd*",fields="$I", expr='ccdfltid?="I"', Stdout="in.I")
	#os.system("cat in.U in.B in.V in.R in.I > dump")
	os.system("cp in.U out.U")			#Make dummy out.U for reduction()
	Breduced=open("out.B","w")
	Vreduced=open("out.V","w")
	Rreduced=open("out.R","w")
	Ireduced=open("out.I","w")
	with open("in.B") as B:
		Braw=B.read().split('\n')
		for i in Braw:
			if i!='':
				Breduced.write('r'+i+'\n')
			else:
				Breduced.write(i+'\n')
	Breduced.close()
	with open("in.V") as V:
		Vraw=V.read().split('\n')
		for i in Vraw:
			if i!='':
				Vreduced.write('r'+i+'\n')
			else:
				Vreduced.write(i+'\n')	
	Vreduced.close()
	with open("in.R") as R:
		Rraw=R.read().split('\n')
		for i in Rraw:
			if i!='':
				Rreduced.write('r'+i+'\n')
			else:
				Rreduced.write(i+'\n')	
	Rreduced.close()
	with open("in.I") as I:
		Iraw=I.read().split('\n')
		for i in Iraw:
			if i!='':
				Ireduced.write('r'+i+'\n')
			else:
				Ireduced.write(i+'\n')	
	Ireduced.close()
	os.system("cat out.U out.B out.V out.R out.I > check")
	os.chdir("calibs")			#os.system("cd wherever") doesnt work o_O
	if len(glob.glob("*dome*.0*")) > 0:
		os.system("rm *dome*.0*")
	if len(glob.glob('*domeB*')) > 0:
		os.system("rm *domeB*")
	if len(glob.glob("*bias.0*")) > 0:
		os.system("rm *bias.0*")
	iraf.hselect(images="*",fields="$I,date-obs,time-obs,ccdfltid,exptime",expr="yes")
	print ("------------------------------")
#	iraf.imstat(images="*ky*[17:1040,3:1026]")
	print ("hsel *ky* $I,ra,dec,ccdfltid,exptime")
	iraf.hselect(images="*ky*",field="$I,ra,dec,ccdfltid,exptime", expr="yes")
	print ("------------------------------")
#	imstat *bi*[17:1040,3:1026]
#	imstat *do*[17:1040,3:1026]
#	imstat *ky*[17:1040,3:1026]
	os.system("mv * ../")
	os.chdir("../")		#new to this version, go back one directory to processed/ level
	return

#def reduction():
#	iraf.processccd()
#	dump=fnmatch.filter(os.listdir('.'),'ccd*fits')
#	for i in dump:
#		os.remove(i)
#	os.system("cp rccd*fits copies/")
	#iraf.postpro()
#	return

#bias and flat correct all the optical data taken
#required: in.{B,V,R,I}, out.{B,V,R,I}, ccd*fits, dome{V,R,I}, skyflatB, bias
#input: none
#output: reduced images, with naming scheme rccd*fits. These are copied to the 'copies' subdirectory
def ccdproc():
	with open("in.B") as B:
		b=B.read()
	if len(b.split('\n'))-1 > 1:
		print str(len(b.split('\n'))-1)+" B images found. Reducing ..."
		iraf.ccdproc(images="@in.B",output="@out.B",overscan="yes",trim="yes",zerocor="yes",darkcor="no",flatcor="yes",readaxis="line",biassec="[2:16,3:1026]",trimsec="[17:1040,3:1026]",zero="*.bias.fits",flat="*.skyflatB.fits",interactive="no",function="spline3",order="11")
	else:
		print "No B images found"
	with open("in.V") as V:
		v=V.read()
	if len(v.split('\n'))-1 > 1:
		print str(len(v.split('\n'))-1)+" V images found. Reducing ..."
		iraf.ccdproc(images="@in.V",output="@out.V",overscan="yes",trim="yes",zerocor="yes",darkcor="no",flatcor="yes",readaxis="line",biassec="[2:16,3:1026]",trimsec="[17:1040,3:1026]",zero="*.bias.fits",flat="*.domeV.fits",interactive="no",function="spline3",order="11")
	else:
		print "No V images found"
	with open("in.R") as R:
		r=R.read()
	if len(r.split('\n'))-1> 1:
		print str(len(r.split('\n'))-1)+" R images found. Reducing ..."	
		iraf.ccdproc(images="@in.R",output="@out.R",overscan="yes",trim="yes",zerocor="yes",darkcor="no",flatcor="yes",readaxis="line",biassec="[2:16,3:1026]",trimsec="[17:1040,3:1026]",zero="*.bias.fits",flat="*.domeR.fits",interactive="no",function="spline3",order="11")
	else:
		print "No R images found"
	with open("in.I") as I:
		i=I.read()
	if len(i.split('\n'))-1> 1:
		print str(len(i.split('\n'))-1)+" I images found. Reducing ..."
		iraf.ccdproc(images="@in.I",output="@out.I",overscan="yes",trim="yes",zerocor="yes",darkcor="no",flatcor="yes",readaxis="line",biassec="[2:16,3:1026]",trimsec="[17:1040,3:1026]",zero="*.bias.fits",flat="*.domeI.fits",interactive="no",function="spline3",order="11")
	else:
		print "No I images found"
	os.system("rm ccd*.[0-9]*.fits")	
	os.system("cp rccd*fits copies/")
	os.system("cp *.dome{R,V,I}.fits /data/yalo180/yalo/SMARTS13m/PROCESSEDCALS")
	os.system("cp *.skyflatB.* /data/yalo180/yalo/SMARTS13m/PROCESSEDCALS")
	os.system("cp *.bias.fits /data/yalo180/yalo/SMARTS13m/PROCESSEDCALS")
	return

#move the reduced ccd data to the appropriate project directory under /data/yalo180/yalo/SMARTS13m/CCD
#required: the data you want to copy
#input: none
#output: owners.lis, a txt file that lists the project owners for the fits files in this directory
#	owners.lis is needed for the ftp upload shell scripts
def CCDsort():
	#os.remove('/data/yalo180/yalo/SMARTS13m/CCD/owners.lis')
	fitsimages=fnmatch.filter(os.listdir('.'),'r*.fits')
	owners=set([pyfits.open(i)[0].header['owner'] for i in fitsimages])
	f=open('/data/yalo180/yalo/SMARTS13m/CCD/owners.lis','w')
	for i in owners:
		#we need the xrb data in the owners file for Dipankar now (ih 140826)
		if (str(i) != 'YALE-08A-0001' and str(i) != 'ALL'):
		#if (str(i) != 'YALE-03A-0001' and str(i) != 'YALE-08A-0001'):
			f.write(str(i)+'\n')
	f.close()
	for i in fitsimages:
		owner=pyfits.open(i)[0].header['owner']
		if owner=='YALE-08A-0001':
			os.system("mv "+ i +" /net/glast/ccd")
		elif owner=='YALE-03A-0001':
			os.system("cp "+ i +' /data/yalo180/yalo/SMARTS13m/CCD/ccddm/')
			os.system("mv "+ i +' /net/xrb/ccd/')
		elif owner=='STANDARD' or owner=='STANDARDFIELD':
			os.system("mv "+ i +' /data/yalo180/yalo/SMARTS13m/CCD/ccdstandards/')
		elif owner=='YALE-03A-0009':
			os.system("mv "+ i +' /data/yalo180/yalo/SMARTS13m/ccdNOAO-08B-0001')
		elif owner!='ALL':
			os.system("mv -v "+ i +" /data/yalo180/yalo/SMARTS13m/CCD/ccd"+owner)
	#iraf.imdelete(images='rccd*fits')		
	return

#move the reduced ir data to the appropriate project directory under /data/yalo180/yalo/SMARTS13m/IR
#required: the data you want to copy
#input: none
#output: owners.lis, a txt file that lists the project owners for the fits files in this directory
#	owners.lis is needed for the ftp upload shell scripts
def IRsort():
	#os.remove('/data/yalo180/yalo/SMARTS13m/CCD/owners.lis')
	fitsimages=fnmatch.filter(os.listdir('.'),'binir*.fits')
	owners=set([pyfits.open(i)[0].header['owner'] for i in fitsimages])
	f=open('/data/yalo180/yalo/SMARTS13m/IR/owners.lis','w')
	for i in owners:
		#we need the xrb data in the owners file for Dipankar now (ih 140826)
		if (str(i) != 'YALE-08A-0001' and str(i) != 'ALL'):
		#if (str(i) != 'YALE-03A-0001' and str(i) != 'YALE-08A-0001'):
			f.write(str(i)+'\n')
	f.close()
	for i in fitsimages:
		owner=pyfits.open(i)[0].header['owner']
		if owner=='YALE-08A-0001':
			os.system("mv -v "+ i +" /net/glast/ir/")
		elif owner=='YALE-03A-0001':
			os.system("cp -v "+ i +" /data/yalo180/yalo/SMARTS13m/IR/irdm/")
			os.system("mv -v "+ i +' /net/xrb/ir/')
		elif owner=='STANDARD' or owner=='STANDARDFIELD':
			os.system("mv -v "+ i +' /data/yalo180/yalo/SMARTS13m/IR/irstandards/')
		elif owner=='YALE-03A-0009':
			os.system("mv -v "+ i +' /data/yalo180/yalo/SMARTS13m/irNOAO-08B-0001')
		elif owner!='ALL':
			os.system("mv -v "+ i +" /data/yalo180/yalo/SMARTS13m/IR/ir"+owner)
	#iraf.imdelete(images='rccd*fits')		
	return

#this function calls the others above and changes directories when needed, to preform the entire reduction process
#required: start in the YYMMDD/ccd/processed direcotry for the date you want to reduce
#	either move calibration frames into this directory, or create new ones using combflat and optdomecomb (above)
#	execute function and everything will (hopefully) work
#input:none
#output:none
def reduceall():
	#filterwheel=['V','R','I']
	#for f in filterwheel:
	#	sort.domecalibs(f)
	speedup()
	ccdproc()
	os.chdir("copies/")
	#os.system("ls")
	CCDsort()
	os.chdir("../../../ir/copies")
	IRsort()
	os.chdir("../../../CCD")
	os.system("./ftpupload.sh")
	os.chdir("../IR")
	os.system("./ftpupload.sh")
	os.chdir("../")
	return